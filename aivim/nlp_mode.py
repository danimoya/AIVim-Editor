"""Explicit NLP submissions use immutable coordinates and reviewed proposals."""
import curses
import json
import re
import time


class NLPHandler:
    def __init__(self,editor):
        self.editor=editor;self.nlp_sections=[];self.live_mode_enabled=editor.settings.ai.nlp_live_mode
        self.force_submission_key=curses.KEY_F9;self._last_revision=-1;self._due=None
        self.selected_context_ids=set();self._scheduled_document_id=None
    @property
    def processing(self):return self.editor.ai_processing
    def enter_nlp_mode(self):self.editor.set_status_message('NLP: explicit #nlp markers; F9 submits; Enter inserts a newline')
    def exit_nlp_mode(self):self._due=None
    def handle_key(self,key):
        if key==self.force_submission_key:self.force_submit();return True
        if key==27:self.exit_nlp_mode();return False
        if self.live_mode_enabled:self._due=time.monotonic()+1.5;self._scheduled_document_id=self.editor.current_tab.document_id
        return False
    def tick(self):
        if self.live_mode_enabled and self._due and time.monotonic()>=self._due and not self.processing:
            self._due=None
            if self.editor.current_tab.document_id!=self._scheduled_document_id:return
            if self.editor.buffer.revision!=self._last_revision:self.force_submit()
    def toggle_live_mode(self):
        self.live_mode_enabled=not self.live_mode_enabled;self.editor.set_status_message('NLP auto-submit '+('enabled; proposals still require review' if self.live_mode_enabled else 'disabled'))
    def cancel_pending_updates(self):self._due=None
    def scan_buffer_for_nlp_sections(self):
        self.nlp_sections=[];opened=None
        for i,line in enumerate(self.editor.buffer.get_lines()):
            stripped=line.strip()
            if re.match(r'^(#|//|<!--)\s*NLP-BEGIN',stripped):opened=i
            elif re.match(r'^(#|//|<!--)\s*NLP-END',stripped):
                if opened is not None:self.nlp_sections.append((opened,i));opened=None
            elif stripped in ('#nlp','//nlp','<!--nlp-->'):
                if opened is None:opened=i
                else:self.nlp_sections.append((opened,i));opened=None
            elif re.match(r'^(#|//|<!--)nlp\s+',stripped):self.nlp_sections.append((i,i))
        if opened is not None:self.editor.set_status_message('Unclosed NLP marker; close it before submitting')
    def select_context(self,document_ids):
        valid={t.document_id for t in self.editor.tabs if t is not self.editor.current_tab}
        if not set(document_ids)<=valid:raise ValueError('Unknown context document')
        self.selected_context_ids=set(document_ids)
    def context_preview(self):
        return [{'document_id':t.document_id,'name':t.name,'content':t.buffer.get_content()} for t in self.editor.tabs if t.document_id in self.selected_context_ids]
    def force_submit(self):
        self.scan_buffer_for_nlp_sections();return self.process_nlp_sections()
    def process_nlp_sections(self):
        if not self.nlp_sections:self.editor.set_status_message('No explicit NLP sections');return False
        ranges=tuple(self.editor.line_offsets(a,b)[0] for a,b,*_ in self.nlp_sections)
        self._last_revision=self.editor.buffer.revision
        instruction=json.dumps({'allowed_ranges':ranges,'context_documents':[c['document_id'] for c in self.context_preview()]})
        return self.editor.submit_ai('nlp',ranges,instruction,json.dumps(self.context_preview()))
    def handle_shift_enter(self):return self.force_submit()
    def handle_ctrl_enter(self):return self.force_submit()
