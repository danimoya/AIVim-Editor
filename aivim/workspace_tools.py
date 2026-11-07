"""Daily editing, recovery, context and model tools for the terminal workspace."""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import threading
import time

from textual.widgets import Button, Checkbox, Input, SelectionList, TextArea
from textual.widgets.text_area import Selection
from .file_store import FileIdentity
from .tui_model import location, offset, Request
from .tui_widgets import ChoiceDialog, PromptDialog, TextDialog
from .checks import syntax_check


class WorkspaceTools:
    def snapshot_session(self):
        if not self.current_id or not self.query("#source-list"): return
        selected = set(self.query_one('#source-list', SelectionList).selected)
        data = {
            'documents': [{'name': d.name, 'content': d.content, 'saved': d.saved,
                'identity': asdict(d.identity) if d.identity else None,
                'cursor': self.areas[d.id].cursor_location, 'intents': d.intents} for d in self.documents.values()],
            'active': list(self.documents).index(self.current_id),
            'sources': [{'name': s.name, 'content': s.content, 'path': s.path,
                         'checked': s.id in selected, 'digest': s.digest, 'chunk': s.chunk} for s in self.sources],
            'preferences': {'vim': self.vim_enabled, 'numbers': self.line_numbers,
                            'pinned': self.sidebar_pinned, 'motion': self.writing_effect,
                            'history': self.remember_history, 'model_profile': self.settings.ai.to_dict()},
            'project': str(self.project.root) if self.project else None,
            'checkpoint': self.last_checkpoint,
            'history': [{'instruction': r.instruction, 'context': r.context, 'original': r.original,
                         'result': r.result, 'state': r.state, 'provider': r.provider,
                         'model': r.model, 'action': r.action} for r in self.records[:50]] if self.remember_history else [],
        }
        try: self.session_store.save(data)
        except OSError: self.say('Recovery snapshot could not be saved; save your buffers explicitly.')

    async def restore_workspace(self):
        data = self.session_store.load()
        if not data: return False
        # Do not run saved instructions or resume old model requests.
        for d in data['documents'][:20]:
            identity = FileIdentity(**d['identity']) if d.get('identity') else None
            doc = await self.new_document(d['name'], d['content'], identity)
            if doc:
                doc.saved = d.get('saved', '')
                doc.intents = d.get('intents', [])
                self.areas[doc.id].move_cursor(tuple(d.get('cursor', (0, 0))))
        if not self.documents: return False
        self.switch_document(list(self.documents)[min(data.get('active', 0), len(self.documents)-1)])
        for s in data.get('sources', [])[:30]:
            self.add_source(s['name'], s['content'])
            self.sources[-1].path = s.get('path', '')
            self.sources[-1].digest = s.get('digest', '')
            self.sources[-1].chunk = s.get('chunk')
            if not s.get('checked', True): self.query_one('#source-list', SelectionList).deselect(self.sources[-1].id)
        for r in data.get('history', [])[:50]:
            record = Request(self.current_id, 0, 0, r['original'], r['action'], r['instruction'], r['context'], r['provider'], r['model'])
            record.state, record.result = r['state'], r['result']; self.records.append(record)
        if data.get('project') and not self.project:
            from .project import Project
            try: self.project = Project(data['project'])
            except (ValueError,OSError): pass
        self.last_checkpoint = data.get('checkpoint')
        self.render_history(); self.refresh_documents()
        self.say('Workspace recovered. Live submission is off; no AI request was resumed.')
        return True

    def action_forget_history(self):
        self.records.clear(); self.remember_history = False
        # Remove persisted history from older snapshots of this configuration too.
        for path in self.session_store.path.parent.glob(self.session_store.key + '*.json'):
            data = self.session_store._load(path)
            if data:
                data['history'] = []
                previous = self.session_store.path
                try:
                    self.session_store.path = path; self.session_store.save(data)
                finally: self.session_store.path = previous
        self.render_history(); self.snapshot_session(); self.say('AI history cleared; history persistence disabled.')

    def action_remember_history(self):
        self.remember_history = not self.remember_history; self.snapshot_session()
        self.say('Remember AI history: ' + str(self.remember_history))

    def action_find(self):
        self.push_screen(PromptDialog('Find · literal text', value=self.search_text), self.find_text)

    def find_text(self, value, backwards=False):
        if not value: return
        self.search_text = value
        text = self.editor.text; start = offset(text, self.editor.selection.start if not self.editor.selection.is_empty else self.editor.cursor_location)
        flags = self.settings.search.ignorecase and not (self.settings.search.smartcase and any(c.isupper() for c in value))
        haystack, needle = (text.casefold(), value.casefold()) if flags and value.isascii() and text.isascii() else (text, value)
        at = haystack.rfind(needle, 0, max(0, start)) if backwards else haystack.find(needle, start + 1)
        if at < 0: at = haystack.rfind(needle) if backwards else haystack.find(needle)
        if at < 0: self.say('No match: ' + value); return
        self.editor.selection = Selection(location(text, at), location(text, at + len(value)))
        self.editor.scroll_cursor_visible(); self.editor.focus(); self.say('Match · n next / N previous')

    def action_find_next(self): self.find_text(self.search_text)
    def action_find_previous(self): self.find_text(self.search_text, True)

    def action_replace(self):
        def found(value):
            if value:
                self.push_screen(PromptDialog('Replace all occurrences of ' + value), lambda replacement: self.replace_all(value, replacement))
        self.push_screen(PromptDialog('Find text to replace'), found)

    def replace_all(self, needle, replacement):
        if replacement is None or not needle: return
        count = self.editor.text.count(needle)
        if not count: self.say('No matches.'); return
        self.editor.history.checkpoint()
        self.editor.replace(self.editor.text.replace(needle, replacement), (0, 0), self.editor.document.end)
        self.editor.history.checkpoint(); self.say(f'Replaced {count} occurrence(s). Undo restores them.')

    def action_goto(self): self.push_screen(PromptDialog('Go to line'), self.goto_line)
    def goto_line(self, value):
        try: row = max(0, min(int(value)-1, self.editor.document.line_count-1))
        except (ValueError, TypeError): return
        self.editor.move_cursor((row, 0)); self.editor.focus()

    def action_indent_settings(self):
        self.push_screen(ChoiceDialog('INDENTATION', [('2', '2 spaces'), ('4', '4 spaces'), ('8', '8 spaces'), ('tab', 'Tabs')]), self.set_indent)
    def set_indent(self, value):
        if not value: return
        self.settings.editor.expandtab = value != 'tab'
        if value != 'tab': self.settings.editor.tabstop = int(value)
        for area in self.areas.values():
            area.indent_type = 'spaces' if self.settings.editor.expandtab else 'tabs'
            area.indent_width = self.settings.editor.tabstop
        self.say('Indentation updated.')

    def action_file_picker(self):
        from .workspace_widgets import FilePicker
        self.push_screen(FilePicker(self.project.root if self.project else Path.cwd()), lambda p: self.run_worker(self.open_document(p)) if p else None)

    def action_validate(self):
        ok, message = syntax_check(self.editor.text, self.editor.language)
        self.push_screen(TextDialog('SYNTAX CHECK', message))

    def action_edit_proposal(self):
        if not self.proposal: self.say('No proposal to edit.'); return
        from .workspace_widgets import EditProposal
        request = self.proposal
        def edited(value):
            if value is not None and self.proposal is request:
                request.replacement = value; self.say('Proposal edited. F8 applies it as one undo step.')
        self.push_screen(EditProposal(request.replacement), edited)

    def action_blocks(self):
        records = [r for r in [self.active, self.proposal, *self.pending, *self.records] if r]
        records = list({r.id: r for r in records}.values())
        if not records: self.say('No blocks yet. F9 enables live instructions.'); return
        def chosen(key):
            r = next((r for r in records if r.id == key), None)
            if not r: return
            def action(value):
                if value == 'stop':
                    r.cancel.set(); r.state = 'Cancelled'
                    self.pending = [p for p in self.pending if p.id != r.id]
                    if self.active is r:
                        self.active = None
                        self.query_one("#submit", Button).disabled = False
                        self.query_one("#cancel", Button).disabled = True
                    if self.proposal is r: self.clear_proposal()
                    self.render_history(); self.pump(); self.update_live_hint()
                elif value == 'retry':
                    doc = self.documents.get(r.document_id)
                    if not doc or doc.content[r.start:r.end] != r.original:
                        self.say('Block changed. Select the revised instruction and generate again.'); return
                    new = self.make_request(doc, r.start, r.end, r.action, r.instruction, live=r.live)
                    if new: self.pending.append(new); self.pump()
            self.push_screen(ChoiceDialog(r.state.upper(), [('stop', 'Cancel this block'), ('retry', 'Retry this block')]), action)
        self.push_screen(ChoiceDialog('BLOCKS', [(r.id, f'{r.state} · {r.instruction[:55]}') for r in records]), chosen)

    def action_refresh_sources(self):
        for source in self.sources:
            if source.path:
                loaded = self.store.load(source.path)
                if loaded:
                    import hashlib
                    source.digest = hashlib.sha256(Path(source.path).read_bytes()).hexdigest()
                    content = loaded.content
                    if source.chunk:
                        a,b=source.chunk;content='\n'.join(content.splitlines()[a-1:b])
                    if len(content.encode()) <= 50*1024: source.content = content
        self.say('File sources refreshed. Existing requests retain their original context.')

    def action_source_status(self):
        rows = []
        for s in self.sources:
            loaded = self.store.load(s.path) if s.path else None
            import hashlib
            same = loaded and (hashlib.sha256(Path(s.path).read_bytes()).hexdigest() == s.digest if s.digest else loaded.content == s.content)
            state = ('current' if same else 'changed or unavailable') if s.path else 'note'
            rows.append(f'{s.name}: {state}')
        self.push_screen(TextDialog('SOURCE FRESHNESS', '\n'.join(rows) or 'No sources.'))

    def action_model_status(self):
        provider = self.query_one('#provider').value
        def check():
            started = time.monotonic()
            try:
                result = self.service.request('query', instruction='Reply with exactly: Connected', provider=provider)
                client = self.service.clients.get(provider)
                transport = getattr(getattr(client, '_client', None), '_transport', None)
                route = getattr(transport, 'last_endpoint', None)
                message = f'{provider} / {result.model}\nConnected in {time.monotonic()-started:.2f}s\nRoute: {route or "configured HTTPS / API endpoint"}\n{result.text[:100]}'
            except Exception as exc: message = f'Connection test failed: {exc}'
            if not self._workspace_closing:
                try: self.call_from_thread(self.push_screen, TextDialog('MODEL CONNECTION', message))
                except RuntimeError: pass
        threading.Thread(target=check, daemon=True).start(); self.say('Testing model connection… editor remains available.')

    def action_writing_effect(self):
        self.writing_effect = not self.writing_effect; self.snapshot_session()
        self.say('Writing effect ' + ('on' if self.writing_effect else 'off'))

    def _profiles_store(self):
        from .session import SessionStore
        store = SessionStore(self.settings.config_path)
        store.path = store.path.with_name('profiles-' + store.path.name)
        return store

    def action_save_profile(self):
        def named(name):
            if not name or len(name) > 80: return
            store = self._profiles_store(); data = store.load() or {'documents': [], 'profiles': {}}
            data.setdefault('profiles', {})[name] = self.settings.ai.to_dict()
            store.save(data); self.say('Saved model profile: ' + name + '. Tokens remain outside profile data.')
        self.push_screen(PromptDialog('Name this model connection'), named)

    def action_model_profiles(self):
        data = self._profiles_store().load() or {}; profiles = data.get('profiles', {})
        if not profiles: self.say('Use Save model profile in Ctrl+P first.'); return
        def chosen(name):
            if not name: return
            if self.active or self.proposal or self.pending:
                self.say('Finish or cancel pending AI work before switching profiles.'); return
            from .settings import AISettings
            from .ai_service import AIService
            self.settings.ai = AISettings.from_dict(profiles[name])
            # A transient token from a different server must never cross profiles.
            credentials = {k:v for k,v in self.service.credentials.items() if k != 'compatible'}
            for client in self.service.clients.values():
                if hasattr(client, 'close'): client.close()
            self.service = AIService(settings=self.settings, credentials=credentials)
            self.query_one('#provider').value = self.settings.ai.default_model
            self.update_context(); self.say('Model profile selected: ' + name)
        self.push_screen(ChoiceDialog('MODEL PROFILES', [(n,n) for n in profiles]), chosen)
