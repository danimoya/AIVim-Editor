"""Small floating surfaces for file navigation and proposal editing."""
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, DirectoryTree, Label, TextArea


class FilePicker(ModalScreen):
    BINDINGS = [('escape', 'dismiss', 'Close')]
    def __init__(self, root): super().__init__(); self.root = root
    def compose(self) -> ComposeResult:
        with Vertical(id='file-picker'):
            yield Label('OPEN FILE · arrows / mouse · Enter · Escape closes')
            yield DirectoryTree(str(self.root), id='file-tree')
    def on_directory_tree_file_selected(self, event): self.dismiss(str(event.path))


class EditProposal(ModalScreen):
    BINDINGS = [('escape', 'dismiss', 'Cancel')]
    def __init__(self, text): super().__init__(); self.text = text
    def compose(self):
        with Vertical(id='proposal-editor'):
            yield Label('EDIT PROPOSAL · document changes only after F8')
            yield TextArea(self.text, id='proposal-text')
            with Horizontal():
                yield Button('Keep changes', id='proposal-keep')
                yield Button('Cancel', id='proposal-cancel')
    def on_button_pressed(self, event):
        self.dismiss(self.query_one('#proposal-text', TextArea).text if event.button.id == 'proposal-keep' else None)
