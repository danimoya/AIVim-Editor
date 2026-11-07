"""Mouse-aware terminal editor, small Vim vocabulary, and workspace dialogs."""

from __future__ import annotations

import re

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea
from textual.widgets.text_area import Selection

from .tui_model import offset, location


class EditorArea(TextArea):
    """Keep native selection/undo; add modal keys without reimplementing text layout."""

    BINDINGS = [
        Binding(key, "modal_motion('" + motion + "')", show=False)
        for key, motion in [
            ("left", "h"),
            ("down", "j"),
            ("up", "k"),
            ("right", "l"),
            ("home", "0"),
            ("end", "$"),
        ]
    ]

    def action_modal_motion(self, motion):
        if self.vim_enabled and self.mode in ("NORMAL", "VISUAL"):
            self._move(motion)
        else:
            {
                "h": self.action_cursor_left,
                "j": self.action_cursor_down,
                "k": self.action_cursor_up,
                "l": self.action_cursor_right,
                "0": self.action_cursor_line_start,
                "$": self.action_cursor_line_end,
            }[motion]()

    class ContextRequested(Message):
        def __init__(self, area, x=None, y=None):
            super().__init__()
            self.area, self.x, self.y = area, x, y

    class ModeChanged(Message):
        pass

    class BlockBoundary(Message):
        def __init__(self, area):
            super().__init__()
            self.area = area

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vim_enabled = True
        self.mode = "NORMAL"
        self.prefix = ""
        self.count = ""
        self.register = ""
        self.visual_anchor = None
        self.visual_cursor = None
        self.visual_line = False
        self.ink_request = None
        self.ink_text = ""
        self.ink_painted = ""

    def advance_ink(self):
        target = self.ink_text
        if target == "Composing…":
            self.ink_painted = target
        else:
            current = self.ink_painted if target.startswith(self.ink_painted) else ""
            remaining = len(target) - len(current)
            # Catch up quickly even if the model sends a large burst. This never
            # adds a long artificial wait and never edits the document itself.
            self.ink_painted = target[:len(current) + max(4, remaining // 5)]
        self.refresh()

    def render_line(self, y):
        # Decorative ink never enters the editable document or its undo history.
        request = self.ink_request
        if request and not request.invalid and request.state in ("Generating", "Awaiting review"):
            from rich.segment import Segment
            from rich.style import Style
            from textual.strip import Strip
            import time
            start_row = location(self.text, request.start)[0]
            end_row = location(self.text, request.end)[0]
            row = self.scroll_offset.y + y
            if start_row <= row <= end_row:
                lines = self.ink_painted.splitlines() or ["Composing…"]
                index = row - start_row
                text = lines[index] if index < len(lines) else ""
                # A soft moving pen at the original block; hide under normal edits.
                pen = " ▍" if index == min(len(lines)-1, end_row-start_row) and int(time.monotonic()*4)%2 else ""
                if getattr(self.app, "streaming_effect", "typing") == "matrix" and text and index == min(len(lines)-1, end_row-start_row):
                    import random
                    generator = random.Random(int(time.monotonic()*12) + row)
                    text = text[:-min(5,len(text))] + "".join(generator.choice("01:+*") for _ in range(min(5,len(text))))
                value = ("  " + text + pen)[self.scroll_offset.x:]
                color = "#76ff9d" if getattr(self.app, "streaming_effect", "typing") == "matrix" else "#b0edba"
                return Strip([Segment(value, Style(color=color, bgcolor="#14271c"))]).adjust_cell_length(self.size.width, Style(bgcolor="#14271c"))
        return super().render_line(y)

    def edit(self, edit):
        # Record exact spans before Textual queues its Changed message. This also
        # disambiguates deleting one of several identical instruction blocks.
        workspace = self.app if self.is_mounted else None
        if workspace and hasattr(workspace, "_sync_document"):
            workspace._sync_document(self)
            start, end = sorted(
                offset(self.text, loc) for loc in (edit.from_location, edit.to_location)
            )
        before_length = len(self.text)
        result = super().edit(edit)
        if workspace and hasattr(workspace, "_sync_document"):
            workspace._sync_document(
                self, (start, end, len(self.text) - before_length + end - start)
            )
        return result

    def undo(self):
        if self.is_mounted and hasattr(self.app, "invalidate_document_requests"):
            self.app.invalidate_document_requests(self)
        super().undo()

    def redo(self):
        if self.is_mounted and hasattr(self.app, "invalidate_document_requests"):
            self.app.invalidate_document_requests(self)
        super().redo()

    def set_mode(self, mode):
        self.mode = mode
        self.prefix = self.count = ""
        if mode != "VISUAL":
            self.visual_anchor = self.visual_cursor = None
        self.post_message(self.ModeChanged())

    async def _on_mouse_down(self, event: events.MouseDown):
        if event.button == 3:
            event.stop()
            event.prevent_default()
            self.post_message(self.ContextRequested(self, event.screen_x, event.screen_y))
            return
        if event.button != 1:
            return
        self.app.auto_hide_sidebar()
        # Mouse selection always works, including while in Vim Normal mode.
        if self.mode == "VISUAL":
            self.set_mode("NORMAL")
        await super()._on_mouse_down(event)

    async def _on_mouse_up(self, event: events.MouseUp):
        if event.button == 1:
            await super()._on_mouse_up(event)

    def _move(self, key, count=1):
        selecting = self.mode == "VISUAL"
        if selecting:
            self.selection = Selection.cursor(self.visual_cursor)
        actions = {
            "h": lambda: self.move_cursor(
                (self.cursor_location[0], max(0, self.cursor_location[1] - 1))
            ),
            "j": self.action_cursor_down,
            "k": self.action_cursor_up,
            "l": lambda: self.move_cursor(
                (
                    self.cursor_location[0],
                    min(
                        len(self.document.get_line(self.cursor_location[0])),
                        self.cursor_location[1] + 1,
                    ),
                )
            ),
            "w": self.action_cursor_word_right,
            "b": self.action_cursor_word_left,
            "0": self.action_cursor_line_start,
            "$": self.action_cursor_line_end,
            "gg": lambda: self.move_cursor((0, 0)),
            "G": lambda: self.move_cursor(
                (
                    self.document.line_count - 1,
                    len(self.document.get_line(self.document.line_count - 1)),
                )
            ),
        }
        if key == "^":
            row, _ = self.cursor_location
            line = self.document.get_line(row)
            self.move_cursor((row, len(line) - len(line.lstrip())))
        elif key == "e":
            pos = offset(self.text, self.cursor_location)
            for _ in range(count):
                match = re.search(r"\w+|[^\w\s]+", self.text[pos + 1 :])
                if match:
                    pos += 1 + match.end() - 1
            self.move_cursor(location(self.text, pos))
        else:
            for _ in range(count):
                actions[key]()
        if selecting:
            self.visual_cursor = self.cursor_location
            a, b = sorted((self.visual_anchor, self.visual_cursor))
            if self.visual_line:
                a = (a[0], 0)
                b = (
                    (b[0] + 1, 0)
                    if b[0] + 1 < self.document.line_count
                    else (b[0], len(self.document.get_line(b[0])))
                )
            else:
                b = location(self.text, min(len(self.text), offset(self.text, b) + 1))
            self.selection = Selection(a, b)

    def _replace(self, value, start, end):
        self.history.checkpoint()
        self.replace(value, start, end, maintain_selection_offset=False)
        self.history.checkpoint()

    async def _on_paste(self, event: events.Paste):
        self.app.prepare_live_edit(self)
        await super()._on_paste(event)

    async def _on_key(self, event: events.Key):
        if event.is_printable:
            self.app.auto_hide_sidebar()
        if event.is_printable and (not self.vim_enabled or self.mode == "INSERT"):
            self.app.prepare_live_edit(self)
        if not self.vim_enabled:
            await super()._on_key(event)
            if event.key == "enter":
                self.app.handle_live_boundary(self)
            return
        if event.key == "escape":
            event.stop()
            event.prevent_default()
            if self.mode == "INSERT":
                self.history.checkpoint()
            self.set_mode("NORMAL")
            self.selection = Selection.cursor(self.cursor_location)
            return
        if self.mode == "INSERT":
            await super()._on_key(event)
            if event.key == "enter":
                self.app.handle_live_boundary(self)
            return
        # App function keys and Ctrl bindings still work; suppress printable inserts.
        if not event.is_printable:
            return
        event.stop()
        event.prevent_default()
        key = event.character
        if key.isdigit() and (self.count or key != "0"):
            self.count = (self.count + key)[-3:]
            return
        count = min(int(self.count or "1"), 999)
        self.count = ""
        if self.prefix:
            command, self.prefix = self.prefix + key, ""
            if command == "gg":
                self._move("gg")
            elif command in ("dd", "yy"):
                row = self.cursor_location[0]
                end_row = min(row + count, self.document.line_count)
                start = (row, 0)
                end = (
                    (end_row, 0)
                    if end_row < self.document.line_count
                    else (end_row - 1, len(self.document.get_line(end_row - 1)))
                )
                self.register = self.document.get_text_range(start, end)
                if command == "dd":
                    if end_row == self.document.line_count and row > 0:
                        start = (row - 1, len(self.document.get_line(row - 1)))
                    self._replace("", start, end)
                if self.register and not self.register.endswith("\n"):
                    self.register += "\n"
            return
        if key in ("h", "j", "k", "l", "w", "b", "e", "0", "^", "$", "G"):
            self._move(key, count)
        elif key in ("g", "d", "y") and self.mode != "VISUAL":
            self.prefix = key
            self.count = str(count)
        elif key == "/":
            self.app.action_find()
        elif key in ("n", "N"):
            self.app.find_text(self.app.search_text, key == "N")
        elif key == ":":
            self.app.action_command()
        elif key == "u":
            self.set_mode("NORMAL")
            self.action_undo()
        elif key in ("v", "V"):
            if self.mode == "VISUAL":
                self.set_mode("NORMAL")
                self.selection = Selection.cursor(self.cursor_location)
            else:
                self.visual_anchor = self.visual_cursor = self.cursor_location
                self.visual_line = key == "V"
                self.mode = "VISUAL"
                self._move("l", 0)
                self.post_message(self.ModeChanged())
        elif key in ("d", "x", "y") and self.mode == "VISUAL":
            self.register = self.selected_text
            if key != "y":
                self._replace("", *self.selection)
            else:
                self.app.copy_to_clipboard(self.register)
            self.set_mode("NORMAL")
        elif key == "x":
            a = offset(self.text, self.cursor_location)
            self._replace(
                "", location(self.text, a), location(self.text, min(a + count, len(self.text)))
            )
        elif key in ("p", "P"):
            if self.register:
                row, col = self.cursor_location
                if self.register.endswith("\n"):
                    if key == "p":
                        at = (
                            (row + 1, 0)
                            if row + 1 < self.document.line_count
                            else (row, len(self.document.get_line(row)))
                        )
                        text = (
                            self.register
                            if row + 1 < self.document.line_count
                            else "\n" + self.register.rstrip("\n")
                        )
                    else:
                        at, text = (row, 0), self.register
                else:
                    at = (row, min(col + (key == "p"), len(self.document.get_line(row))))
                    text = self.register
                self._replace(text, at, at)
        elif key in ("i", "a", "A", "I", "o", "O"):
            self.selection = Selection.cursor(self.cursor_location)
            if key == "a":
                row, col = self.cursor_location
                self.move_cursor((row, min(col + 1, len(self.document.get_line(row)))))
            elif key == "A":
                self.action_cursor_line_end()
            elif key == "I":
                self._move("^")
            elif key in ("o", "O"):
                row, _ = self.cursor_location
                at = (row, 0) if key == "O" else (row, len(self.document.get_line(row)))
                self._replace("\n", at, at)
                self.move_cursor((row, 0) if key == "O" else (row + 1, 0))
            self.history.checkpoint()
            self.set_mode("INSERT")


class PromptDialog(ModalScreen):
    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def __init__(self, title, *, value="", placeholder=""):
        super().__init__()
        self.title_text, self.value, self.placeholder = title, value, placeholder

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text, markup=False, id="dialog-title")
            yield Input(value=self.value, placeholder=self.placeholder, id="dialog-input")
            with Horizontal(classes="dialog-buttons"):
                yield Button("Continue", id="dialog-ok", variant="primary")
                yield Button("Cancel", id="dialog-cancel")

    def on_mount(self):
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted):
        self.dismiss(event.value)

    def on_button_pressed(self, event: Button.Pressed):
        self.dismiss(self.query_one(Input).value if event.button.id == "dialog-ok" else None)


class ChoiceDialog(ModalScreen):
    # Focus after layout without an animated scroll: a tall menu in a small
    # terminal must not move its mouse targets while the user is clicking.
    AUTO_FOCUS = ""
    BINDINGS = [
        ("escape", "dismiss(None)", "Cancel"),
        ("down", "next_choice", "Next"),
        ("up", "previous_choice", "Previous"),
    ]

    def on_mouse_down(self, event: events.MouseDown):
        if not self.query_one("#dialog").region.contains(event.screen_x, event.screen_y):
            event.stop()
            self.dismiss(None)

    def action_next_choice(self):
        self.focus_next()

    def action_previous_choice(self):
        self.focus_previous()

    def __init__(self, title, choices, *, x=None, y=None):
        super().__init__()
        self.title_text, self.choices, self.x, self.y = title, choices, x, y

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text, markup=False, id="dialog-title")
            for value, label in self.choices:
                yield Button(label, id="choice-" + value)
            yield Button("Cancel  [Esc]", id="choice-cancel")

    def on_mount(self):
        if self.x is not None:
            dialog = self.query_one("#dialog")
            dialog.styles.width = min(42, self.size.width)
            dialog.styles.dock = "top"
            dialog.styles.margin = (
                max(0, min(self.y, self.size.height - len(self.choices) - 5)),
                0,
                0,
                max(0, min(self.x, self.size.width - 42)),
            )
        self.query_one(Button).focus(scroll_visible=False)

    def on_button_pressed(self, event: Button.Pressed):
        value = event.button.id.removeprefix("choice-")
        self.dismiss(None if value == "cancel" else value)


class TextDialog(ModalScreen):
    BINDINGS = [("escape", "dismiss(None)", "Close")]

    def __init__(self, title, text):
        super().__init__()
        self.title_text, self.text = title, text

    def compose(self):
        with Vertical(id="text-dialog"):
            yield Label(self.title_text, markup=False)
            yield TextArea(self.text, read_only=True, soft_wrap=True, id="dialog-text")
            yield Button("Close  [Esc]", id="text-close")

    def on_button_pressed(self):
        self.dismiss(None)


class NoteDialog(ModalScreen):
    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def compose(self):
        with Vertical(id="note-dialog"):
            yield Label("SOURCE NOTE // reference material", id="dialog-title")
            yield Input(placeholder="Name this source", id="note-name")
            yield TextArea(
                placeholder="Paste reference text, style guidance or project context…",
                id="note-content",
                soft_wrap=True,
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Add source", id="note-add", variant="primary")
                yield Button("Cancel", id="note-cancel")

    def on_mount(self):
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "note-cancel":
            self.dismiss(None)
        else:
            name, content = self.query_one(Input).value.strip(), self.query_one(TextArea).text
            if name and content.strip():
                self.dismiss((name, content))


class ConnectionDialog(ModalScreen):
    """One place to paste a route, choose a served model and set HTTPS trust."""

    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def __init__(self, settings, credentials=None):
        super().__init__()
        self.settings = settings
        self.credentials = credentials or {}

    def compose(self):
        from textual.widgets import Checkbox, Select

        with VerticalScroll(id="connection-dialog"):
            yield Label("CONNECT MODEL // OpenShift · OpenAI-compatible HTTPS", id="dialog-title")
            yield Label("HTTPS API URL (route URL or /v1 base)")
            yield Input(
                value=self.settings.ai.compatible_base_url,
                placeholder="https://model.apps.example.com/v1",
                id="connect-url",
            )
            yield Label("Bearer token (optional; masked)")
            yield Input(
                password=True,
                placeholder="Paste a token, or use AIVIM_COMPATIBLE_API_KEY",
                id="connect-token",
            )
            yield Checkbox(
                "Remember token in a private file on this computer",
                value=bool(self.settings.ai.compatible_token_file),
                id="connect-remember",
            )
            yield Label("Private CA certificate file (optional)")
            yield Input(
                value=self.settings.ai.compatible_ca_file,
                placeholder="/path/to/cluster-ca.pem",
                id="connect-ca",
            )
            yield Button(
                "Discover models",
                id="connect-discover",
                tooltip="Check HTTPS/authentication and fetch available model IDs",
            )
            yield Select([], prompt="Select a discovered model", id="connect-models")
            yield Label("Model ID (can also be entered manually)")
            yield Input(
                value=self.settings.ai.compatible_model,
                placeholder="The model ID returned by /v1/models",
                id="connect-model",
            )
            yield Static(
                "TLS certificates are always verified. Tokens are stored only if you choose Remember.",
                id="connect-status",
                markup=False,
            )
            with Horizontal(classes="dialog-buttons"):
                yield Button("Save & use", id="connect-save", variant="primary")
                yield Button("Cancel", id="connect-cancel")

    def on_mount(self):
        self.query_one("#connect-url").focus()

    def get_connection(self):
        from textual.widgets import Checkbox
        from .compatible import Connection, normalize_url

        token = self.query_one("#connect-token", Input).value.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return Connection(
            normalize_url(self.query_one("#connect-url", Input).value),
            self.query_one("#connect-model", Input).value.strip(),
            token,
            self.query_one("#connect-ca", Input).value.strip(),
            self.query_one("#connect-remember", Checkbox).value,
        )

    def on_select_changed(self, event):
        if event.select.id == "connect-models" and isinstance(event.value, str):
            self.query_one("#connect-model", Input).value = event.value

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "connect-cancel":
            self.dismiss(None)
        elif event.button.id == "connect-discover":
            try:
                connection = self.get_connection()
                from .compatible import token_for

                token = connection.token or token_for(self.settings, self.credentials)
            except (ValueError, OSError):
                self.query_one("#connect-status", Static).update(
                    "Check the HTTPS URL and configured token file."
                )
                return
            self.query_one("#connect-discover", Button).disabled = True
            self.query_one("#connect-status", Static).update(
                "Checking HTTPS connection and model list…"
            )
            self.discover(connection, token)
        elif event.button.id == "connect-save":
            try:
                connection = self.get_connection()
                if not connection.model:
                    raise ValueError("Enter a model ID or discover models first.")
                if connection.ca_file:
                    from .compatible import ssl_context

                    ssl_context(connection.ca_file)
                self.dismiss(connection)
            except (ValueError, OSError) as exc:
                self.query_one("#connect-status", Static).update(str(exc))

    from textual import work

    @work(thread=True, exit_on_error=False)
    def discover(self, connection, token):
        from .compatible import discover_models
        import httpx

        try:
            models = discover_models(connection.base_url, token, connection.ca_file)
            message = f"Connected securely. {len(models)} model(s) available."
        except ValueError as exc:
            models = []
            message = str(exc)
        except (httpx.HTTPError, OSError):
            models = []
            message = "Connection failed. Check the route, network and CA certificate."
        try:
            self.app.call_from_thread(self.discovery_finished, models, message)
        except RuntimeError:
            pass

    def discovery_finished(self, models, message):
        from textual.widgets import Select

        if not self.is_mounted:
            return
        self.query_one("#connect-status", Static).update(message)
        self.query_one("#connect-discover", Button).disabled = False
        if models:
            selector = self.query_one("#connect-models", Select)
            selector.set_options([(model, model) for model in models])
            selector.value = models[0]
