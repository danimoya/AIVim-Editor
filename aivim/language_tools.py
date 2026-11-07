"""Explicit language-server tools, integrated with project change review."""
from __future__ import annotations
import json
from pathlib import Path
import queue
import shlex
import threading
from urllib.parse import unquote,urlsplit
from textual.widgets.text_area import Selection
from .language_server import LanguageClient,utf16_position,character_location
from .project import ChangeSet
from .tui_model import location,offset
from .tui_widgets import ChoiceDialog,PromptDialog,TextDialog


def uri_path(uri):
    parsed=urlsplit(uri)
    if parsed.scheme!='file' or parsed.netloc not in ('','localhost'):raise ValueError('Only local file definitions are supported.')
    import os
    path=unquote(parsed.path)
    if os.name=='nt' and len(path)>2 and path[0]=='/' and path[2]==':':path=path[1:]
    return Path(path)


class LanguageTools:
    def safe_language_action(self, callback, *args):
        try: return callback(*args)
        except (ValueError,TypeError,KeyError,IndexError,OSError) as exc: self.say("Invalid language-server response: "+str(exc))

    def action_language_start(self):
        if not self.project:self.action_project_open();return
        def entered(value):
            if not value:return
            try:argv=shlex.split(value)
            except ValueError as exc:self.say(str(exc));return
            if not argv:return
            def worker():
                try:
                    client=LanguageClient(argv,self.project.root)
                    self._project_deliver(self.language_started,client)
                except (ValueError,OSError) as exc:self._project_deliver(self.say,'Language server: '+str(exc))
            threading.Thread(target=worker,daemon=True).start();self.say('Starting explicitly selected language server…')
        self.push_screen(PromptDialog('Start stdio language server · executable and arguments',placeholder='pylsp'),entered)

    def language_started(self,client):
        if self.language_client:self.language_client.close()
        self.language_client=client;self.language_documents={};self.language_diagnostics={}
        self.language_sync();self.say('Language server connected. Ctrl+P: completion, definition, rename, diagnostics.')

    def language_sync(self):
        client=self.language_client
        if not client or client.closed or not self.current_id:return None
        d=self.document
        if not d.identity:self.say('Save this buffer before using language tools.');return None
        uri=Path(d.identity.target).as_uri()
        previous=self.language_documents.get(uri)
        try:
            if not previous:
                client.open_document(d.identity.target,d.content,self.editor.language)
                self.language_documents[uri]=(1,d.content)
            elif previous[1]!=d.content:
                version=previous[0]+1;client.change_document(uri,d.content,version)
                self.language_documents[uri]=(version,d.content)
        except (OSError,ValueError) as exc:self.say(str(exc));return None
        return uri

    def drain_language(self):
        if not self.language_client:return
        for _ in range(32):
            try:event=self.language_client.notifications.get_nowait()
            except queue.Empty:break
            if event.get('method')=='textDocument/publishDiagnostics':
                params=event.get('params',{});self.language_diagnostics[params.get('uri','')]=params.get('diagnostics',[])[:500]

    def action_diagnostics(self):
        self.language_sync();rows=[]
        for uri,diagnostics in self.language_diagnostics.items():
            for d in diagnostics:
                rows.append(f"{uri}:{d['range']['start']['line']+1}: {d['message']}")
        self.push_screen(TextDialog('LANGUAGE DIAGNOSTICS','\n'.join(rows) or 'No diagnostics received. Start a language server and save/open a file.'))

    def language_request(self,method,callback,extra=None):
        uri=self.language_sync()
        if not uri:self.say('Connect a language server and save the buffer first.');return
        doc=self.document;source=doc.content;client=self.language_client
        params={'textDocument':{'uri':uri},'position':utf16_position(source,self.editor.cursor_location),**(extra or {})}
        def worker():
            try:
                result=client.request(method,params)
                def finished():
                    if self.current_id!=doc.id or doc.content!=source:self.say('Document changed; request language action again.');return
                    self.safe_language_action(callback,result,source)
                self._project_deliver(finished)
            except (OSError,ValueError) as exc:self._project_deliver(self.say,str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def action_completion(self):
        cursor=self.editor.cursor_location;selection=self.editor.selection
        def completed(result,source):
            items=result.get('items',[]) if isinstance(result,dict) else result or []
            items=items[:100]
            if not items:self.say('No completions.');return
            def chosen(key):
                if key is None:return
                if self.editor.text!=source:self.say('Completion is stale.');return
                item=items[int(key)];edit=item.get('textEdit')
                if item.get('insertTextFormat')==2:self.say('Snippet completion is not supported; choose a plain-text item.');return
                if edit:
                    r=edit.get('range') or edit.get('replace');a=character_location(source,r['start']);b=character_location(source,r['end']);text=edit['newText']
                else:
                    row,col=cursor;line=source.split('\n')[row];start=col
                    while start and (line[start-1].isalnum() or line[start-1]=='_'):start-=1
                    a,b=(row,start),cursor;text=item.get('insertText',item['label'])
                self.editor.replace(text,a,b);self.editor.focus()
            self.push_screen(ChoiceDialog('COMPLETION',[(str(i),item['label'][:100]) for i,item in enumerate(items)]),lambda key:self.safe_language_action(chosen,key))
        self.language_request('textDocument/completion',completed)

    def action_definition(self):
        def defined(result,source):
            candidates=result if isinstance(result,list) else [result] if result else []
            if not candidates:self.say('No definition.');return
            def chosen(key):
                if key is None:return
                target=candidates[int(key)];uri=target.get('uri',target.get('targetUri'));r=target.get('range',target.get('targetSelectionRange'))
                try:path=uri_path(uri)
                except ValueError as exc:self.say(str(exc));return
                async def open_at():
                    if await self.open_document(str(path)):
                        self.editor.move_cursor(character_location(self.editor.text,r['start']))
                self.run_worker(open_at())
            self.push_screen(ChoiceDialog('DEFINITION',[(str(i),c.get('uri',c.get('targetUri',''))[-100:]) for i,c in enumerate(candidates)]),lambda key:self.safe_language_action(chosen,key))
        self.language_request('textDocument/definition',defined)

    def action_rename_symbol(self):
        if not self.project:self.action_project_open();return
        if any(d.dirty for d in self.documents.values()):self.say('Save project buffers before a multi-file rename.');return
        def asked(name):
            if not name:return
            snapshots_before={};remaining=32*1024*1024
            for path in self.project.files():
                loaded=self.store.load(self.project.path(path))
                if loaded:
                    remaining-=len(loaded.content.encode())
                    if remaining<0:break
                    snapshots_before[path]=loaded
            def renamed(result,source):
                if not result:self.say('No rename edits.');return
                changes=dict(result.get('changes',{}))
                for row in result.get('documentChanges',[]):
                    if 'textDocument' not in row:
                        self.say('Resource operations require manual file management.');return
                    changes[row['textDocument']['uri']]=row['edits']
                snapshots={};files=[]
                try:
                    for uri,edits in changes.items():
                        path=uri_path(uri);name=str(path.resolve().relative_to(self.project.root));loaded=snapshots_before.get(name)
                        if not loaded:raise ValueError('Rename target was not in the project snapshot.')
                        snapshots[name]=loaded;text=loaded.content;ranges=[]
                        for e in edits:
                            a=offset(text,character_location(text,e['range']['start']));b=offset(text,character_location(text,e['range']['end']))
                            ranges.append((a,b,e['newText']))
                        for left,right in zip(sorted(ranges),sorted(ranges)[1:]):
                            if left[1]>right[0]:raise ValueError('Overlapping rename edits.')
                        for a,b,replacement in sorted(ranges,reverse=True):text=text[:a]+replacement+text[b:]
                        files.append({'path':name,'content':text})
                    self.review_project(ChangeSet.parse(self.project,json.dumps({'files':files}),snapshots))
                except (ValueError,OSError,KeyError) as exc:self.say('Rename rejected: '+str(exc))
            self.language_request('textDocument/rename',renamed,{'newName':name})
        self.push_screen(PromptDialog('Rename symbol to'),asked)
