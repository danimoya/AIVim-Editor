"""Project context, change review, persistent intent and explicit test execution."""
from __future__ import annotations
import json
from pathlib import Path
import threading
from textual.widgets import SelectionList
from .project import Project, ChangeSet, digest
from .project_widgets import ContextPicker, ChangeReview
from .tui_widgets import ChoiceDialog, PromptDialog, TextDialog
from .interface_widgets import ProjectPrompt, ProjectInstruction


class ProjectTools:
    def action_project_open(self):
        def chosen(value):
            if not value:return
            try:self.project=Project(value)
            except (ValueError,OSError) as exc:self.say(str(exc));return
            self.session_store.project=str(self.project.root)
            self.say('Project: '+str(self.project.root)+'. Context is selected explicitly.');self.snapshot_session()
        self.push_screen(PromptDialog('Open project folder',value=str(self.project.root) if self.project else str(Path.cwd())),chosen)

    def action_project_search(self):
        if not self.project:self.action_project_open();return
        def search(query):
            if not query:return
            project=self.project
            def worker():
                try:candidates=project.search(query)
                except (ValueError,OSError) as exc:self._project_deliver(self.say,str(exc));return
                if not candidates:self._project_deliver(self.say,'No matching project files or symbols.');return
                def add(rows):
                    for c in rows or []:
                        count=len(self.sources)
                        self.add_source(f"{c['path']}:{c['start']}–{c['end']}",c['text'])
                        if len(self.sources)>count:
                            self.sources[-1].path=str(project.path(c['path']))
                            self.sources[-1].digest=c['digest']
                            self.sources[-1].chunk=(c['start'],c['end'])
                self._project_deliver(self.push_screen,ContextPicker(candidates),add)
            threading.Thread(target=worker,daemon=True).start();self.say('Searching file paths and symbols…')
        self.push_screen(PromptDialog('Search project files / symbols / text'),search)

    def _project_deliver(self, callback, *args):
        if not self._workspace_closing:
            try:self.call_from_thread(callback,*args)
            except RuntimeError:pass

    def action_project_generate(self):
        if not self.project:self.action_project_open();return
        if self.active or self.proposal or self.project_busy:self.say('Finish the current AI proposal first.');return
        def asked(instruction):
            if not instruction:return
            references = instruction.references if isinstance(instruction, ProjectInstruction) else []
            instruction = instruction.text if isinstance(instruction, ProjectInstruction) else instruction
            if not instruction.strip(): return
            project=self.project;selected=set(self.query_one('#source-list',SelectionList).selected)
            names=[]
            for s in self.sources:
                if s.id in selected and s.path:
                    try:name=str(Path(s.path).resolve().relative_to(project.root))
                    except ValueError:continue
                    if name not in names:names.append(name)
            readonly_references=[]
            for ref in references:
                doc=self.documents.get(ref.document_id)
                if doc:
                    self._sync_document(self.areas[doc.id])
                if ref.path and (not doc or not doc.dirty):
                    try:
                        name=str(Path(ref.path).resolve().relative_to(project.root))
                        project.path(name)
                    except ValueError:
                        name=None
                    if name is not None:
                        if name not in names:names.append(name)
                        continue
                if doc:
                    text=doc.content
                    if ref.path:
                        try: names.remove(str(Path(ref.path).resolve().relative_to(project.root)))
                        except ValueError: pass
                else:
                    try:
                        path=Path(ref.path)
                        if not path.is_file() or path.stat().st_size>50*1024:raise ValueError('Mentioned file is missing or exceeds 50 KiB.')
                        loaded=self.store.load(path)
                        if not loaded:raise ValueError(loaded.message)
                        text=loaded.content
                    except (OSError,ValueError) as exc:self.say(str(exc));return
                readonly_references.append({'name':ref.label,'content':text,'read_only':True,'unsaved':bool(doc and doc.dirty)})
            try:snapshots=project.snapshots(names)
            except (ValueError,OSError) as exc:self.say(str(exc));return
            context=json.dumps({'references':readonly_references,'files':[{'path':n,'content':v.content} for n,v in snapshots.items()],
                                'notes':[{'name':s.name,'content':s.content} for s in self.sources if s.id in selected and not s.path]})
            if len(context.encode())>50*1024:self.say('Project context exceeds 50 KiB. Choose fewer/smaller files.');return
            provider=self.query_one('#provider').value
            self.project_busy=True
            cancellation=threading.Event();self.project_cancel=cancellation
            def worker():
                try:
                    result=self.service.request('project',context=context,instruction=instruction+'\nReturn only a JSON object {"files":[{"path":"relative/path","content":"complete new file text"}]}. Change only the supplied existing files or create new files. No Markdown.',provider=provider,cancel=cancellation)
                    plan=ChangeSet.parse(project,result.text,snapshots)
                    self._project_deliver(self.review_project,plan)
                except Exception as exc:self._project_deliver(self.say,'Project proposal failed; files unchanged: '+str(exc))
                finally:self.project_busy=False
            threading.Thread(target=worker,daemon=True).start();self.say('Preparing project proposal… files stay unchanged until review.')
        self.push_screen(ProjectPrompt(self.mention_candidates()),asked)

    def review_project(self, plan):
        def chosen(selected):
            if not selected:return
            try:
                targets={str(plan.project.path(c.path)) for c in plan.changes}
                if any(d.dirty and d.identity and d.identity.target in targets for d in self.documents.values()):raise ValueError('Save or discard open unsaved target buffers before applying project changes.')
                self.last_checkpoint=str(plan.apply(selected));self.change_set=plan
                self.reload_project_buffers(targets)
                self.snapshot_session();self.say('Project changes applied. Roll back checkpoint is available in Ctrl+P.')
            except (ValueError,OSError) as exc:self.say(str(exc))
        self.push_screen(ChangeReview(plan),chosen)

    def reload_project_buffers(self, targets):
        for d in self.documents.values():
            if d.identity and d.identity.target in targets:
                loaded=self.store.load(d.identity.target)
                if loaded:
                    area=self.areas[d.id];area.history.checkpoint()
                    area.replace(loaded.content,(0,0),area.document.end);area.history.checkpoint()
                    d.content=loaded.content;d.saved=loaded.content;d.identity=loaded.identity
        self.refresh_documents()

    def action_project_rollback(self):
        if not self.last_checkpoint or not self.project:self.say('No project checkpoint in this workspace.');return
        checkpoint=Path(self.last_checkpoint)
        try:data=json.loads(checkpoint.read_text(encoding='utf-8'))
        except (ValueError,OSError) as exc:self.say(str(exc));return
        def chosen(key):
            if key!='rollback':return
            try:
                targets={str(self.project.path(r['path'])) for r in data['files']}
                if any(d.dirty and d.identity and d.identity.target in targets for d in self.documents.values()):raise ValueError('Save or discard unsaved target buffers before rollback.')
                ChangeSet(self.project,[]).rollback(checkpoint)
                self.reload_project_buffers(targets);self.say('Checkpoint rolled back.');self.snapshot_session()
            except (ValueError,OSError) as exc:self.say(str(exc))
        self.push_screen(ChoiceDialog('ROLL BACK PROJECT CHECKPOINT', [('rollback','Restore files if they have no newer edits')]),chosen)

    def action_intent_blocks(self):
        blocks=self.document.intents
        if not blocks:self.say('Accept a generated block first. Its instruction will remain attached.');return
        def chosen(key):
            block=next((b for b in blocks if b['id']==key),None)
            if not block:return
            area=self.editor;doc=self.document
            current=doc.content[block['start']:block['end']]
            def asked(instruction):
                if not instruction:return
                if doc.content[block['start']:block['end']]!=current:self.say('Block changed while refining. Try again.');return
                request=self.make_request(doc,block['start'],block['end'],'generate',instruction)
                if not request:return
                request.context=json.dumps({'sources':json.loads(request.context),'current_block':current,'manually_edited':block.get('edited',False)})
                if len(request.context.encode())>50*1024:self.say('Block context exceeds 50 KiB.');return
                request.intent_id=block['id'];self.pending.append(request);self.pump()
            state=' · manually edited; review preserves your choice' if block.get('edited') or current!=block['generated'] else ''
            self.push_screen(PromptDialog('Refine this instruction'+state,value=block['instruction']),asked)
        self.push_screen(ChoiceDialog('INSTRUCTION BLOCKS',[(b['id'],('Edited · ' if b.get('edited') else '')+b['instruction'][:60]) for b in blocks]),chosen)

    def action_run_command(self):
        if not self.project:self.action_project_open();return
        from .runner import CommandRun
        import shlex
        def entered(value):
            if not value:return
            try:argv=shlex.split(value)
            except ValueError as exc:self.say(str(exc));return
            if not argv:return
            def approved(key):
                if key!='run':return
                if self.command_run and not self.command_run.finished.is_set():self.say('A command is already running.');return
                run=CommandRun(argv,self.project.root);self.command_run=run
                def worker():
                    run.execute()
                    self._project_deliver(self.command_finished,run)
                threading.Thread(target=worker,daemon=True).start();self.say('Command running. Ctrl+P → Stop command cancels it.')
            self.push_screen(ChoiceDialog('RUN IN '+str(self.project.root),[('run','Run: '+shlex.join(argv))]),approved)
        self.push_screen(PromptDialog('Command / test · arguments, no shell expansion'),entered)

    def command_finished(self,run):
        text=f"$ {' '.join(run.argv)}\nExit: {run.returncode}\n\n{run.output}"
        def chosen(value):
            if value=='source':self.add_source('Command output',text[-48*1024:])
            elif value=='fix':
                self.add_source('Command output',text[-48*1024:]);self.action_project_generate()
        self.push_screen(TextDialog('COMMAND OUTPUT',text))
        self.last_command_output=text
        self.say('Output ready. Ctrl+P → Use command output / Fix from test output.')

    def action_command_context(self):
        if self.last_command_output:self.add_source('Command output',self.last_command_output[-48*1024:])
        else:self.say('Run a command first.')
    def action_fix_from_output(self):self.action_command_context();self.action_project_generate()
    def action_stop_command(self):
        if self.command_run:self.command_run.cancel();self.say('Command cancellation requested.')

    def action_project_menu(self):
        choices=[('open','Open project…'),('search','Find files / symbols / context…'),('generate','Generate multi-file change…'),
                 ('rollback','Roll back checkpoint…'),('run','Run command / tests…'),('language','Start language server…'),
                 ('complete','Completion…'),('definition','Definition…'),('rename','Rename symbol…'),('diagnostics','Diagnostics…')]
        callbacks={'open':self.action_project_open,'search':self.action_project_search,'generate':self.action_project_generate,
                   'rollback':self.action_project_rollback,'run':self.action_run_command,'language':self.action_language_start,
                   'complete':self.action_completion,'definition':self.action_definition,'rename':self.action_rename_symbol,'diagnostics':self.action_diagnostics}
        self.push_screen(ChoiceDialog('PROJECT',choices),lambda key:callbacks[key]() if key in callbacks else None)

    def action_project_checkpoints(self):
        if not self.project:self.action_project_open();return
        from .session import SessionStore
        store=SessionStore(self.project.root/'project-context')
        key=digest(str(self.project.root))[:16];choices=[]
        for path in sorted(store.path.parent.glob('checkpoint-'+key+'-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[:30]:
            try:data=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,ValueError):continue
            if data.get('root')==str(self.project.root) and data.get('state')!='rolled back':
                choices.append((str(path),data.get('state','unknown')+' · '+', '.join(r['path'] for r in data['files'])[:75]))
        if not choices:self.say('No project checkpoints.');return
        def chosen(path):
            if path:self.last_checkpoint=path;self.action_project_rollback()
        self.push_screen(ChoiceDialog('PROJECT CHECKPOINTS · includes interrupted writes',choices),chosen)
