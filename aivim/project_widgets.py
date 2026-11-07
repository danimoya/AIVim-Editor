"""Project search and per-hunk change review, always temporary overlays."""
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, SelectionList, TextArea


class ContextPicker(ModalScreen):
    BINDINGS=[('escape','dismiss','Close')]
    def __init__(self, candidates): super().__init__();self.candidates=candidates
    def compose(self):
        with Vertical(id='project-dialog'):
            yield Label('PROJECT CONTEXT · select exact chunks to send')
            yield SelectionList(*[(f"{c['path']}:{c['start']}–{c['end']}",i,False) for i,c in enumerate(self.candidates)],id='context-candidates')
            yield TextArea('',read_only=True,id='candidate-preview')
            yield Button('Add checked sources',id='context-add')
    def on_selection_list_selection_highlighted(self,event):
        c=self.candidates[event.selection.value]
        self.query_one('#candidate-preview',TextArea).load_text(c['path']+'\n\n'+c['text'])
    def on_button_pressed(self,event):
        self.dismiss([self.candidates[i] for i in self.query_one('#context-candidates',SelectionList).selected])


class ChangeReview(ModalScreen):
    BINDINGS=[('escape','dismiss','Reject')]
    def __init__(self, changeset):super().__init__();self.changeset=changeset
    def compose(self):
        with Vertical(id='project-dialog'):
            yield Label('REVIEW PROJECT CHANGES · selected hunks will be written to files')
            options=[]
            for f,c in enumerate(self.changeset.changes):
                for h,(_,a,b,_,_) in enumerate(c.hunks()):options.append((f'{c.path} · hunk {h+1} · lines {a+1}–{max(a+1,b)}',(f,h),True))
            yield SelectionList(*options,id='change-hunks')
            yield TextArea(''.join(c.diff() for c in self.changeset.changes),read_only=True,id='change-preview')
            with Horizontal(classes='button-row'):
                yield Button('Apply checked hunks',id='changes-apply')
                yield Button('Reject',id='changes-reject')
    def on_selection_list_selection_highlighted(self,event):
        self.query_one('#change-preview',TextArea).load_text(self.changeset.changes[event.selection.value[0]].diff())
    def on_button_pressed(self,event):
        self.dismiss(self.query_one('#change-hunks',SelectionList).selected if event.button.id=='changes-apply' else None)
