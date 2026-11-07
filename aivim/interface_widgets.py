"""Focused project prompts, file completion, preferences and a short startup scene."""
from __future__ import annotations
from dataclasses import dataclass
import random
from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Label, OptionList, Select, Static, TextArea
from .file_mentions import mention_prefix, referenced_files
from .tui_model import offset, location


@dataclass
class ProjectInstruction:
    text: str
    references: list


class ModeButton(Button):
    async def _on_click(self, event):
        event.stop()
        self.press()


class MentionArea(TextArea):
    BINDINGS = [Binding(key, action, show=False) for key, action in [
        ('down', 'mention_down'), ('up', 'mention_up'), ('tab', 'mention_pick'),
        ('enter', 'mention_pick'), ('escape', 'mention_hide')]]

    def check_action(self, action, parameters):
        if action.startswith('mention_'):
            return bool(self.screen.matches) and self.screen.query_one('#file-completions').display
        return super().check_action(action, parameters)

    def action_mention_down(self): self.screen.query_one('#file-completions', OptionList).action_cursor_down()
    def action_mention_up(self): self.screen.query_one('#file-completions', OptionList).action_cursor_up()
    def action_mention_pick(self): self.screen.accept_mention()
    def action_mention_hide(self): self.screen.hide_mentions()


class ProjectPrompt(ModalScreen):
    BINDINGS = [Binding('ctrl+enter', 'submit_prompt', 'Generate', priority=True),
                Binding('escape', 'dismiss(None)', 'Cancel')]

    def __init__(self, candidates):
        super().__init__(); self.candidates = candidates; self.matches = []; self.suppressed = None

    def compose(self) -> ComposeResult:
        with Vertical(id='project-prompt-dialog'):
            yield Label('Describe the project change', id='project-prompt-title')
            yield MentionArea(soft_wrap=True, id='project-instruction',
                              placeholder='Describe the change…\n@ mentions an open or recent file')
            yield OptionList(id='file-completions', markup=False, compact=True)
            yield Static('Enter: new line · @: files · ↑↓ / Tab: choose · Ctrl+Enter: generate', id='project-prompt-hint', markup=False)
            with Horizontal(classes='button-row'):
                yield Button('Generate', id='project-prompt-submit', variant='primary')
                yield Button('Cancel', id='project-prompt-cancel')

    def on_mount(self):
        self.query_one('#file-completions').display = False
        self.query_one('#project-instruction').focus()

    @on(TextArea.Changed, '#project-instruction')
    @on(TextArea.SelectionChanged, '#project-instruction')
    def update_mentions(self):
        area = self.query_one('#project-instruction', TextArea)
        prefix = mention_prefix(area.text, offset(area.text, area.cursor_location))
        listing = self.query_one('#file-completions', OptionList)
        if not prefix or prefix == self.suppressed:
            self.matches = []; listing.display = False; return
        query = prefix[2].casefold()
        matches = [c for c in self.candidates if query in c.label.casefold()][:8]
        if matches != self.matches:
            self.matches = matches
            listing.clear_options()
            listing.add_options([f'{c.label}  ·  {c.origin}' for c in matches])
            listing.highlighted = 0 if matches else None
        listing.display = bool(matches)

    def hide_mentions(self):
        area = self.query_one('#project-instruction', TextArea)
        self.suppressed = mention_prefix(area.text, offset(area.text, area.cursor_location))
        self.matches = []; self.query_one('#file-completions').display = False

    def accept_mention(self):
        listing = self.query_one('#file-completions', OptionList)
        if listing.highlighted is None or not self.matches: return
        candidate = self.matches[listing.highlighted]
        area = self.query_one('#project-instruction', TextArea)
        prefix = mention_prefix(area.text, offset(area.text, area.cursor_location))
        if not prefix: return
        area.replace(candidate.token + ' ', location(area.text, prefix[0]), location(area.text, prefix[1]))
        self.matches = []; listing.display = False; area.focus()

    def on_option_list_option_selected(self, event):
        self.query_one('#file-completions', OptionList).highlighted = event.option_index
        self.accept_mention()

    def action_submit_prompt(self):
        text = self.query_one('#project-instruction', TextArea).text
        if text.strip(): self.dismiss(ProjectInstruction(text, referenced_files(text, self.candidates)))

    def on_button_pressed(self, event):
        if event.button.id == 'project-prompt-submit': self.action_submit_prompt()
        elif event.button.id == 'project-prompt-cancel': self.dismiss(None)


class SettingsDialog(ModalScreen):
    BINDINGS = [('escape', 'dismiss(None)', 'Cancel')]
    def __init__(self, values): super().__init__(); self.values = values
    def compose(self):
        v = self.values
        with VerticalScroll(id='settings-dialog'):
            yield Label('SETTINGS // make it yours', classes='section-title')
            yield Label('Editing')
            yield Checkbox('Vim-style input', value=v['vim'], id='setting-vim')
            yield Checkbox('Line numbers', value=v['numbers'], id='setting-numbers')
            yield Checkbox('Indent with tabs', value=v['tabs'], id='setting-tabs')
            yield Select([(f'{n} columns', str(n)) for n in [2, 4, 8]], value=str(v['indent']), allow_blank=False, id='setting-indent')
            yield Label('Animation effects')
            yield Checkbox('Reduce motion · use instant updates', value=v['reduce_motion'], id='setting-reduce-motion')
            yield Label('AI generation activity')
            yield Select([('Spinner', 'spinner'), ('Pulse', 'pulse'), ('Matrix', 'matrix'), ('Off', 'off')], value=v['ai_animation'], allow_blank=False, id='setting-ai-animation')
            yield Label('App loading')
            yield Select([('Matrix + AIVIM ASCII', 'matrix'), ('Off', 'off')], value=v['startup_effect'], allow_blank=False, id='setting-startup')
            yield Button('Preview loading effect', id='settings-preview')
            yield Label('Live code replacement')
            yield Select([('Typing / pen', 'typing'), ('Instant', 'instant'), ('Matrix', 'matrix')], value=v['streaming_effect'], allow_blank=False, id='setting-streaming')
            yield Label('History')
            yield Checkbox('Remember AI history on this computer', value=v['history'], id='setting-history')
            yield Static('Live mode is changed from the top bar and always starts off after recovery.', markup=False)
            with Horizontal(classes='button-row'):
                yield Button('Save settings', id='settings-save', variant='primary')
                yield Button('Cancel', id='settings-cancel')

    def on_button_pressed(self, event):
        if event.button.id == 'settings-preview':
            self.app.push_screen(MatrixLoading()); return
        if event.button.id == 'settings-cancel': self.dismiss(None); return
        if event.button.id != 'settings-save': return
        checked = lambda name: self.query_one('#setting-' + name, Checkbox).value
        selected = lambda name: self.query_one('#setting-' + name, Select).value
        self.dismiss({'vim': checked('vim'), 'numbers': checked('numbers'), 'tabs': checked('tabs'),
                      'indent': int(selected('indent')), 'reduce_motion': checked('reduce-motion'),
                      'ai_animation': selected('ai-animation'), 'startup_effect': selected('startup'),
                      'streaming_effect': selected('streaming'), 'history': checked('history')})


LOGO = [r'   _    _____     _____ __  __ ', r'  / \  |_ _\ \   / /_ _|  \/  |',
        r' / _ \  | | \ \ / / | || |\/| |', r'/ ___ \ | |  \ V /  | || |  | |',
        r'/_/   \_\___|  \_/  |___|_|  |_|']


class MatrixLoading(ModalScreen):
    BINDINGS = [('escape', 'dismiss(None)', 'Skip')]
    def __init__(self): super().__init__(); self.frame = 0
    def compose(self): yield Static('', id='startup-matrix')
    def on_mount(self):
        self.paint(); self.set_interval(.06, self.paint); self.set_timer(.65, self.finish)
    def finish(self):
        if self.is_current: self.dismiss(None)

    def paint(self):
        self.frame += 1; width = self.size.width; height = self.size.height
        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        randomizer = random.Random(self.frame // 2)
        for x in range(0, width, 3):
            head = (x * 7 + self.frame * 2) % max(1, height)
            for trail in range(7):
                y = head - trail
                if 0 <= y < height: canvas[y][x] = randomizer.choice('01AIVIM:+')
        top = max(0, height // 2 - 3)
        for n, line in enumerate(LOGO + ['       write in a rhythm']):
            if top + n >= height: break
            start = max(0, (width - len(line)) // 2)
            for i, char in enumerate(line[:width]): canvas[top+n][start+i] = char
        text = Text('\n'.join(''.join(row) for row in canvas), style='#356b44 on #0c1411')
        for row in range(top, min(height, top + len(LOGO))): text.stylize('bold #b0edba', row*(width+1), (row+1)*(width+1)-1)
        self.query_one('#startup-matrix', Static).update(text)
    def on_key(self, event: events.Key):
        if event.key == 'escape': return
        event.stop(); event.prevent_default()
        key, character = event.key, event.character
        self.dismiss(None)
        self.app.call_after_refresh(lambda: self.app.post_message(events.Key(key, character)))
