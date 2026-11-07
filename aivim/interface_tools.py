"""Compact buffer navigation, live mode controls, animations and preferences."""
from pathlib import Path
from rich.text import Text
import time
from textual.widgets import Button, Checkbox, Select, Static, TextArea
from .file_mentions import file_candidates
from .interface_widgets import MatrixLoading, SettingsDialog
from .languages import infer_language, highlight_language


class InterfaceTools:
    def remember_file(self, path):
        path = str(Path(path).expanduser().resolve())
        self.recent_files = [path] + [p for p in self.recent_files if p != path][:49]
        try: self.user_preferences.update({'recent_files': self.recent_files})
        except OSError: self.say('Recent-file history could not be saved.')

    def mention_candidates(self):
        return file_candidates(self.documents.values(), self.recent_files, self.project.root if self.project else None)

    def refresh_buffer_tabs(self):
        container = self.query_one('#buffer-tabs')
        for key in list(self._buffer_buttons):
            if key not in self.documents:
                self._buffer_buttons.pop(key).remove()
        for key, doc in self.documents.items():
            button = self._buffer_buttons.get(key)
            if button is None:
                button = Button('', id='buffer-' + key, classes='buffer-tab', compact=True)
                self._buffer_buttons[key] = button
                container.mount(button)
            name = doc.name
            if doc.identity and sum(d.name == doc.name for d in self.documents.values()) > 1:
                name = Path(doc.identity.target).parent.name + '/' + doc.name
            button.label = Text(('● ' if doc.dirty else '') + name)
            button.tooltip = (doc.identity.target if doc.identity else doc.name) + ' · click to switch'
            button.set_class(key == self.current_id, 'active-buffer')

    def scroll_active_tab(self):
        button = self._buffer_buttons.get(self.current_id)
        if button and button.is_mounted and not self._workspace_closing: button.scroll_visible(animate=False)

    def action_cycle_live_mode(self):
        live = self.query_one('#live', Checkbox); auto = self.query_one('#auto', Checkbox)
        if not live.value:
            auto.value = False; live.value = True; mode = 'Live review'
        elif not auto.value:
            auto.value = True; mode = 'Live auto-replace'
        else:
            auto.value = False; live.value = False; mode = 'Edit'
        self.update_titlebar(); self.say(mode + ' mode')

    def update_live_button(self):
        live = self.query_one('#live', Checkbox).value
        auto = self.query_one('#auto', Checkbox).value
        button = self.query_one('#live-mode', Button)
        button.label = 'LIVE / auto' if live and auto else 'LIVE / review' if live else 'EDIT'
        button.set_class(live, 'live-on'); button.set_class(live and auto, 'auto-on')

    def tick_ai_activity(self):
        self.refresh_fullscreen_controls()
        busy = bool(self.active or self.project_busy)
        frame = int(time.monotonic() * 8)
        effect = 'off' if self.reduce_motion else self.ai_animation
        patterns = {'spinner': ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'],
                    'pulse': ['·', '∙', '●', '∙'], 'matrix': ['01▒', '▓10', '1▒0', '10▓']}
        value = patterns[effect][frame % len(patterns[effect])] if busy and effect in patterns else '…' if busy else ''
        if value != self._activity_value:
            self._activity_value = value
            self.query_one('#ai-activity', Static).update(value)

    def check_action(self, action, parameters):
        if self.is_running and isinstance(self.screen, MatrixLoading): return False
        if action == 'leave_ai_fullscreen': return self.ai_fullscreen and len(self.screen_stack) == 1
        if action == 'submit' and len(self.screen_stack) > 1: return False
        return super().check_action(action, parameters)

    def action_fullscreen_ai(self):
        if self.ai_fullscreen: self.action_leave_ai_fullscreen(); return
        self._ai_before_fullscreen = (self.sidebar_visible, self.sidebar_pinned)
        self.ai_fullscreen = True; self.sidebar_visible = True
        self.query_one('#workspace-tabs').active = 'editor-tab'
        self.update_sidebar()
        self.call_after_refresh(self.query_one('#result', TextArea).focus)

    def action_leave_ai_fullscreen(self):
        if not self.ai_fullscreen: return
        self.ai_fullscreen = False
        self.sidebar_visible, self.sidebar_pinned = self._ai_before_fullscreen or (True, False)
        self._ai_before_fullscreen = None
        self.update_sidebar()
        if not self.sidebar_visible: self.editor.focus()
        else: self.query_one('#fullscreen-ai', Button).focus()

    def settings_values(self):
        return {'vim': self.vim_enabled, 'numbers': self.line_numbers,
                'tabs': not self.settings.editor.expandtab,
                'indent': self.settings.editor.tabstop if self.settings.editor.tabstop in (2, 4, 8) else 4,
                'reduce_motion': self.reduce_motion, 'ai_animation': self.ai_animation,
                'startup_effect': self.startup_effect, 'streaming_effect': self.streaming_effect,
                'history': self.remember_history}

    def action_settings(self): self.push_screen(SettingsDialog(self.settings_values()), self.apply_user_settings)

    def apply_user_settings(self, values):
        if values is None: return
        try: self.user_preferences.update(values)
        except OSError: self.say('Settings could not be saved; preferences were not changed.'); return
        self.vim_enabled = values['vim']; self.line_numbers = values['numbers']
        self.settings.editor.expandtab = not values['tabs']; self.settings.editor.tabstop = values['indent']
        self.ai_animation = values['ai_animation']; self.startup_effect = values['startup_effect']
        self.streaming_effect = values['streaming_effect']; self.reduce_motion = values['reduce_motion']
        self.writing_effect = not self.reduce_motion and self.streaming_effect != 'instant'
        self.remember_history = values['history']
        for area in self.areas.values():
            area.vim_enabled = self.vim_enabled
            area.set_mode('NORMAL' if self.vim_enabled else 'STANDARD')
            area.show_line_numbers = self.line_numbers
            area.indent_type = 'tabs' if values['tabs'] else 'spaces'
            area.indent_width = values['indent']
        self.snapshot_session(); self.update_selection(); self.say('Settings saved.')

    def inferred_language(self, doc, instruction=''):
        opened = []
        for other in self.documents.values():
            if other.id == doc.id: continue
            if self.project and other.identity and not Path(other.identity.target).is_relative_to(self.project.root): continue
            opened.append((other.name, other.content, bool(other.identity)))
        return infer_language(doc.name, doc.content, instruction, opened, saved=bool(doc.identity))

    def refresh_language(self, doc):
        area = self.areas[doc.id]
        language = highlight_language(self.inferred_language(doc), area.available_languages)
        if area.language != language:
            selection, scroll = area.selection, area.scroll_offset
            area.language = language
            area.selection = selection
            area.scroll_to(scroll.x, scroll.y, animate=False)

    def refresh_fullscreen_controls(self):
        self.query_one("#ai-request-controls").display = not self.ai_fullscreen or bool(self.active)
        self.query_one("#ai-review-controls").display = not self.ai_fullscreen or bool(self.proposal)

    def update_ai_response(self, text):
        result = self.query_one('#result', TextArea)
        position = result.scroll_offset
        follow = result.scroll_y >= result.max_scroll_y - 1
        result.load_text(text)
        if self.ai_fullscreen:
            if follow: self.call_after_refresh(result.scroll_end, animate=False)
            else: self.call_after_refresh(result.scroll_to, position.x, position.y, animate=False)

    async def on_event(self, event):
        from textual import events
        if isinstance(event, (events.Key, events.Paste)) and self.is_running and isinstance(self.screen, MatrixLoading):
            # Remove the decoration before normal routing; never replay or reorder typing.
            self.screen.finish()
        await super().on_event(event)
