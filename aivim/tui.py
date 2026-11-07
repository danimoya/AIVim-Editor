"""A terminal-first, mouse-aware AI workspace with explicit source context."""

from __future__ import annotations

import json
from pathlib import Path
import queue
import threading
import time

from textual import on, events
from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll, Container
from textual.theme import Theme
from textual.widgets import (
    Button,
    Collapsible,
    Checkbox,
    Footer,
    Input,
    Label,
    RichLog,
    Select,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)
from textual.widgets.text_area import Selection

from ._version import __version__
from .ai_jobs import AIJob
from .ai_service import AIError, AIService
from .file_store import FileStore
from .proposals import parse_proposal
from .settings import Settings
from .session import SessionStore
from .workspace_tools import WorkspaceTools
from .tui_model import (
    Document,
    Request,
    Source,
    changed_span,
    completed_block,
    location,
    map_position,
    map_request,
    offset,
    partial_code,
)
from .tui_widgets import (
    ChoiceDialog,
    EditorArea,
    PromptDialog,
    TextDialog,
    NoteDialog,
    ConnectionDialog,
)

HELP = """AIVIM // TERMINAL WORKBENCH

F1 Help     F2 Context menu     F3 Sources     F4 Vim / standard keys
F5 Generate F6 Explain          F7 Rewrite     F8 Accept change
F9 Live     F10 Quit            Ctrl+S Save    Ctrl+O Open
Ctrl+N New  Ctrl+W Close buffer  Ctrl+Q Quit    Ctrl+Enter Ask AI
Ctrl+Z Undo Ctrl+R Redo         Ctrl+P Command palette · Connect HTTPS model
Alt+1 Editor   Alt+2 Sources    Alt+3 History    Alt+A floating AI workbench

MOUSE
Click to place the cursor; drag to select. Right-click the editor to open
selection actions without losing the selection. Hover over buttons for help.
F2 opens the same menu when a terminal reserves right-click for its own menu.
The AI button / Alt+A opens the floating Workbench. Pin keeps it open while
you edit; Collapse restores the editor width. Connect HTTPS model configures
an OpenShift/OpenAI-compatible URL, model, masked token and optional CA file.
Shift+mouse usually uses the terminal's native selection/copy behavior.

VIM KEYS (F4 toggles standard editing)
i/a/A/I/o/O enter Insert mode; Esc returns to Normal.
h/j/k/l, w/b/e, 0/^/$, gg/G navigate. Numeric counts work with motions,
dd, yy and x. v/V select characters/lines with letter motions.
x/dd delete, yy/y copy to the internal register, p/P paste, u undo.
Ctrl+R redo. A right-click or mouse drag can also select text in Normal mode.
:w / :w! / :w path / :wq / :q / :q! / :e path / :new / :tabnext / :tabprev
This is a useful Vim vocabulary, not the complete Vim runtime or plugin API.

SOURCES & AI
Add source files or notes in Sources. Check which ones each request may use.
Context preview shows the exact selected snapshots and optional nearby text.
Select text before Explain/Rewrite/Analyze. Generate inserts at the cursor;
New with AI creates a new buffer first. Provider/model settings are shared
with the classic editor. Remote output streams into a read-only preview.
Only a complete, validated proposal can be accepted. Every accepted change
is one undo step. Nothing is executed automatically.

LIVE BLOCKS
Enable Live on a blank line. A single Enter continues an instruction;
a blank line submits it. Keep typing the next block while AI works.
Review is the default. Auto replace is an explicit opt-in, and replaces
only a complete instruction whose text hasn't changed. Undo restores it.
Pasting, undo and redo never submit by themselves. Cancel clears the queue.
Turn Live off to edit ordinary code. At most ten blocks wait in the queue.

FILES & SESSION
Save writes through the transactional FileStore, preserving loaded encoding,
newline convention, symlinks and permissions, and checking external changes.
Buffers, cursors, sources and preferences recover locally. AI history is opt-in.
Ctrl+P: Remember AI history / Clear AI history. Live is always off after recovery.
AI requests are limited to 50 KiB of selection/context and 8 KiB instructions.
Ctrl+F Find · Ctrl+H Replace · Ctrl+G Line · / n N search in Vim mode.
Ctrl+P also exposes Blocks, source freshness, model profiles and syntax checks.
"""


class TerminalWorkspace(WorkspaceTools, App):
    TITLE = f"AIVim {__version__} // Terminal Workbench"
    CSS_PATH = "tui.tcss"
    ENABLE_COMMAND_PALETTE = True
    BINDINGS = [
        Binding("ctrl+f", "find", "Find", priority=True),
        Binding("ctrl+h", "replace", "Replace", priority=True),
        Binding("ctrl+g", "goto", "Go to line", priority=True),
        Binding("f1", "help", "Help", priority=True),
        Binding("f2", "context_menu", "Actions", priority=True),
        Binding("f3", "sources", "Sources", priority=True),
        Binding("f4", "toggle_vim", "Vim/Type", priority=True),
        Binding("f5", "generate", "Generate", priority=True),
        Binding("f6", "explain", "Explain", priority=True),
        Binding("f7", "rewrite", "Rewrite", priority=True),
        Binding("f8", "accept", "Accept", priority=True),
        Binding("f9", "toggle_live", "Live", priority=True),
        Binding("f10", "quit", "Quit", priority=True),
        Binding("ctrl+s", "save", "Save", show=False, priority=True),
        Binding("ctrl+o", "open", "Open", show=False, priority=True),
        Binding("ctrl+n", "new", "New", show=False, priority=True),
        Binding("ctrl+w", "close_document", "Close", show=False, priority=True),
        Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
        Binding("ctrl+enter", "submit", "Ask AI", show=False, priority=True),
        Binding("ctrl+r", "redo", "Redo", show=False, priority=True),
        Binding("alt+a", "toggle_ai", "AI panel", show=False, priority=True),
        Binding("alt+1", "editor", "Editor", show=False, priority=True),
        Binding("alt+2", "sources", "Sources", show=False, priority=True),
        Binding("alt+3", "history", "History", show=False, priority=True),
    ]

    def __init__(self, filename=None, *, settings=None, service=None, connect_on_start=False, restore_session=False):
        super().__init__()
        self.settings = settings or Settings()
        self.filename = filename
        self.connect_on_start = connect_on_start
        self.restore_session = restore_session
        self.session_store = SessionStore(self.settings.config_path, unique=True)
        preferences = (self.session_store.load() or {}).get("preferences", {})
        if restore_session and preferences.get("model_profile"):
            from .settings import AISettings
            self.settings.ai = AISettings.from_dict(preferences["model_profile"])
        self.service = service or AIService(settings=self.settings)
        self.search_text = ""
        self.writing_effect = preferences.get("motion", True)
        self.remember_history = preferences.get("history", False)
        self._ink_ready_at = 0.0
        self.sidebar_pinned = False
        self.sidebar_visible = False
        self._ai_focus_requested = False
        self.store = FileStore()
        self.documents = {}
        self.areas = {}
        self.current_id = None
        self.sources = []
        self.records = []
        self.pending = []
        self.active = None
        self.proposal = None
        self.mailbox = queue.Queue(maxsize=256)
        self.raw_preview = ""
        self.vim_enabled = preferences.get("vim", True)
        self.line_numbers = preferences.get("numbers", self.settings.editor.number)
        self._workspace_closing = False
        self.register_theme(
            Theme(
                name="aivim-phosphor",
                primary="#84dca0",
                secondary="#d6ac66",
                accent="#d6ac66",
                foreground="#c9ddc7",
                background="#0c1411",
                surface="#111e18",
                panel="#15271e",
                success="#84dca0",
                warning="#e7b65e",
                error="#e28b7e",
                dark=True,
            )
        )
        self.theme = "aivim-phosphor"

    def compose(self) -> ComposeResult:
        with Horizontal(id="title-bar"):
            yield Button(
                "≡", id="main-menu", tooltip="Files, sources, live options and view settings"
            )
            yield Static(" AIVim", id="masthead", markup=False)
            yield Button("AI", id="ai-toggle", tooltip="Floating AI Workbench · Alt+A")
        with TabbedContent(initial="editor-tab", id="workspace-tabs"):
            with TabPane("01 EDITOR", id="editor-tab"):
                with Horizontal(id="file-bar"):
                    yield Select([], allow_blank=True, prompt="Documents", id="documents")
                    yield Button("New", id="new", tooltip="New buffer · Ctrl+N")
                    yield Button(
                        "AI New",
                        id="new-ai",
                        tooltip="Create a new buffer and describe it in natural language",
                    )
                    yield Button("Open", id="open", tooltip="Open a file · Ctrl+O")
                    yield Button("Save", id="save", tooltip="Save to disk · Ctrl+S")
                    yield Button("Close", id="close", tooltip="Close buffer · Ctrl+W")
                with Horizontal(id="workbench"):
                    with Vertical(id="editing-pane"):
                        with Horizontal(id="editor-tools"):
                            yield Static("NORMAL", id="mode")
                            yield Button(
                                "F2 Actions",
                                id="actions",
                                tooltip="Right-click or F2 for selection actions",
                            )
                            yield Button(
                                "F4 Vim/Type",
                                id="vim",
                                tooltip="Toggle Vim modal keys and standard typing",
                            )
                            yield Button(
                                "Undo",
                                id="undo",
                                tooltip="Undo · u in Normal mode, Ctrl+Z in standard mode",
                            )
                            yield Button("Redo", id="redo", tooltip="Redo · Ctrl+R")

                        yield Container(id="editor-stack")
                        yield Static(
                            "Select with mouse or v/V · Right-click / F2 for AI actions",
                            id="selection-status",
                            markup=False,
                        )
                        with Horizontal(id="live-bar"):
                            yield Checkbox(
                                "Live blocks",
                                id="live",
                                tooltip="Enter twice submits an instruction block · F9",
                            )
                            yield Checkbox(
                                "Auto replace",
                                id="auto",
                                tooltip="Replace intact instructions only after generation finishes; undo restores them",
                            )
                        yield Static(
                            "ENTER continues · BLANK LINE submits · KEEP TYPING while AI works",
                            id="live-hint",
                            markup=False,
                        )
                    with VerticalScroll(id="ai-panel"):
                        with Horizontal(id="ai-panel-tools"):
                            yield Button(
                                "Pin", id="pin-ai", tooltip="Keep the sidebar open while editing"
                            )
                            yield Button(
                                "Collapse",
                                id="hide-ai",
                                tooltip="Collapse the AI Workbench · Alt+A",
                            )
                        yield Select(
                            [
                                ("Rewrite selection", "improve"),
                                ("Generate at cursor", "generate"),
                                ("Explain selection", "explain"),
                                ("Analyze selection", "analyze"),
                                ("Ask a question", "query"),
                            ],
                            value="improve",
                            allow_blank=False,
                            id="ai-action",
                        )
                        yield TextArea(
                            placeholder="Describe what to create or change…",
                            id="instruction",
                            soft_wrap=True,
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                "Ask AI",
                                id="submit",
                                variant="primary",
                                tooltip="Submit · Ctrl+Enter (if your terminal supports it)",
                            )
                            yield Button(
                                "Cancel",
                                id="cancel",
                                disabled=True,
                                tooltip="Cancel active generation and clear queued blocks",
                            )
                        yield TextArea(
                            "Select text or describe something new.\n\nResponses stream here; your document stays editable.",
                            read_only=True,
                            soft_wrap=True,
                            id="result",
                            show_cursor=False,
                        )
                        with Horizontal(classes="button-row"):
                            yield Button(
                                "Accept [F8]", id="accept", variant="primary", disabled=True
                            )
                            yield Button("Reject", id="reject", disabled=True)
                        with Collapsible(title="Model & sources", collapsed=True, id="ai-details"):
                            yield Button(
                                "Connect HTTPS model…",
                                id="connect-model",
                                tooltip="Set up an OpenShift or OpenAI-compatible endpoint",
                            )
                            yield Select(
                                [
                                    ("HTTPS / OpenShift" if p == "compatible" else p, p)
                                    for p in self.service.models()
                                ],
                                value=self.service.current_model,
                                allow_blank=False,
                                id="provider",
                                tooltip="Provider and model from your AIVim configuration",
                            )
                            yield Static("", id="model-name", markup=False)
                            with Horizontal(id="context-bar"):
                                yield Static("0 sources", id="context-count", markup=False)
                                yield Button(
                                    "Context",
                                    id="context",
                                    tooltip="Inspect the context transmitted to AI",
                                )
                            yield Checkbox(
                                "Nearby text",
                                value=True,
                                id="nearby",
                                tooltip="Include up to 2,000 characters before and after the target",
                            )
            with TabPane("02 SOURCES", id="sources-tab"):
                yield Static(
                    " CONTEXT LIBRARY // Check sources for the next request. Unchecked sources stay local.",
                    classes="section-title",
                    markup=False,
                )
                with Horizontal(id="source-tools"):
                    yield Button(
                        "Add file",
                        id="source-file",
                        tooltip="Add a read-only text snapshot as context",
                    )
                    yield Button("Add note", id="source-note")
                    yield Button("Current buffer", id="source-buffer")
                    yield Button("Remove", id="source-remove")
                with Horizontal(id="source-body"):
                    yield SelectionList(id="source-list")
                    yield TextArea(
                        "Add files or notes, then check what AI may read.",
                        read_only=True,
                        soft_wrap=True,
                        id="source-preview",
                        show_cursor=False,
                    )
            with TabPane("03 HISTORY", id="history-tab"):
                yield Static(
                    " SESSION HISTORY // Prompts, context snapshots, proposals and decisions. Cleared on exit.",
                    classes="section-title",
                    markup=False,
                )
                yield RichLog(id="history-log", wrap=True, markup=False, highlight=False)
        yield Static(
            "F2 actions · Ctrl+P commands · Alt+A AI · F1 help",
            id="status",
            markup=False,
        )
        yield Footer()

    async def on_mount(self):
        recovered = await self.restore_workspace() if self.restore_session and not self.filename and not self.connect_on_start else False
        if recovered:
            pass
        elif self.filename:
            if not await self.open_document(self.filename):
                await self.new_document()
        else:
            await self.new_document()
        self.set_interval(0.04, self.drain_ai)
        self.set_interval(2, self.snapshot_session)
        self.update_context()
        self.resize_layout()
        self.editor.focus()
        self.sidebar_pinned = bool((self.session_store.load() or {}).get("preferences", {}).get("pinned", False))
        self.sidebar_visible = self.sidebar_pinned
        self.update_sidebar()
        if self.connect_on_start:
            self.call_after_refresh(self.action_connect_model)

    @property
    def document(self):
        return self.documents[self.current_id]

    @property
    def editor(self):
        return self.areas[self.current_id]

    def say(self, message):
        self.query_one("#status", Static).update(message)
        self.update_titlebar()

    def resize_layout(self):
        workbench = self.query_one("#workbench")
        workbench.set_class(self.size.width < 100, "narrow")
        workbench.set_class(self.size.height < 36, "compact")
        self.update_sidebar()
        self.query_one("#file-bar").set_class(self.size.width < 75, "small")

    def on_resize(self, event: events.Resize):
        if self.current_id:
            self.call_after_refresh(self.resize_layout)

    async def new_document(self, name=None, content="", identity=None):
        if len(self.documents) >= 20:
            self.say("Twenty buffers are open. Close a buffer before opening another.")
            return None
        name = name or f"untitled-{len(self.documents) + 1}.py"
        doc = Document(name, content, content if identity else "", identity)
        self.documents[doc.id] = doc
        language = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
            ".md": "markdown",
            ".json": "json",
            ".sh": "bash",
            ".css": "css",
            ".html": "html",
        }.get(Path(name).suffix)
        area = EditorArea(
            content,
            language=language,
            soft_wrap=False,
            show_line_numbers=self.line_numbers,
            tab_behavior="indent",
            id="doc-" + doc.id,
            tooltip="Drag to select · Right-click / F2 for actions · F4 for standard typing",
        )
        area.indent_width = self.settings.editor.tabstop
        area.indent_type = "spaces" if self.settings.editor.expandtab else "tabs"
        area.vim_enabled = self.vim_enabled
        area.mode = "NORMAL" if self.vim_enabled else "STANDARD"
        area.border_title = name
        self.areas[doc.id] = area
        await self.query_one("#editor-stack").mount(area)
        self.refresh_documents()
        self.switch_document(doc.id)
        self.refresh_documents()
        return doc

    def switch_document(self, document_id):
        if document_id not in self.documents:
            return
        self.current_id = document_id
        for key, area in self.areas.items():
            area.display = key == document_id
        if self.query_one("#documents", Select).value != document_id:
            selector = self.query_one("#documents", Select)
            with selector.prevent(Select.Changed):
                selector.value = document_id
        doc = self.document
        if self.query_one("#live", Checkbox).value and doc.live_from is None:
            doc.live_from = offset(doc.content, self.editor.cursor_location)
        self.update_selection()
        self.editor.focus()

    def refresh_documents(self):
        selector = self.query_one("#documents", Select)
        options = [(("* " if d.dirty else "") + d.name, d.id) for d in self.documents.values()]
        if getattr(self, "_document_options", None) != options:
            self._document_options = options
            with selector.prevent(Select.Changed):
                selector.set_options(options)
                if self.current_id:
                    selector.value = self.current_id
        for key, area in self.areas.items():
            area.border_title = ("* " if self.documents[key].dirty else "") + self.documents[
                key
            ].name

    async def open_document(self, filename):
        try:
            path = Path(filename).expanduser()
            if path.exists() and path.stat().st_size > 20 * 1024 * 1024:
                self.say("Local editing limit is 20 MiB.")
                return False
            result = self.store.load(filename)
        except (OSError, ValueError):
            self.say("Cannot open this path.")
            return False
        if not result:
            self.say(result.message)
            return False
        for doc in self.documents.values():
            if doc.identity and doc.identity.target == result.identity.target:
                self.switch_document(doc.id)
                self.say("File is already open; switched to its buffer.")
                return True
        doc = await self.new_document(path.name, result.content, result.identity)
        if doc:
            self.say("Opened " + path.name + ". Nothing sent to AI.")
        return bool(doc)

    def _sync_document(self, area, change=None):
        document_id = area.id.removeprefix("doc-")
        doc = self.documents.get(document_id)
        if not doc or area.text == doc.content:
            return
        start, end, inserted = (
            change if change is not None else changed_span(doc.content, area.text)
        )
        targets = [self.active, self.proposal, *self.pending]
        seen = set()
        for target in targets:
            if target and target.id not in seen and target.document_id == document_id:
                seen.add(target.id)
                map_request(target, start, end, inserted)
        if doc.live_from is not None:
            doc.live_from = map_position(doc.live_from, start, end, inserted)
        doc.content = area.text
        if self.proposal and self.proposal.invalid:
            self.proposal.state = "Stale"
            self.clear_proposal()
            self.render_history()
            self.say("Stale proposal: selected text changed. Your edits are preserved.")
        self.refresh_documents()

    def invalidate_document_requests(self, area):
        document_id = area.id.removeprefix("doc-")
        for request in [self.active, self.proposal, *self.pending]:
            if request and request.document_id == document_id:
                request.invalid = True

    @on(TextArea.Changed)
    def text_changed(self, message: TextArea.Changed):
        if isinstance(message.text_area, EditorArea):
            self._sync_document(message.text_area)
            self.update_selection()

    @on(TextArea.SelectionChanged)
    def selection_changed(self, message: TextArea.SelectionChanged):
        if isinstance(message.text_area, EditorArea) and self.current_id:
            self.update_selection()

    @on(EditorArea.ModeChanged)
    def mode_changed(self):
        self.update_selection()

    def update_selection(self):
        if not self.current_id:
            return
        area = self.editor
        self.query_one("#mode", Static).update(area.mode if area.vim_enabled else "STANDARD")
        size = len(area.selected_text)
        row, col = area.cursor_location
        self.query_one("#selection-status", Static).update(
            f" Ln {row + 1} : Col {col + 1}  │  {size} selected  │  Right-click / F2 for actions"
        )
        self.update_titlebar()
        self.update_context()

    def update_titlebar(self):
        if not self.current_id:
            return
        row, col = self.editor.cursor_location
        mode = self.editor.mode if self.editor.vim_enabled else "TYPE"
        flags = " · LIVE" if self.query_one("#live", Checkbox).value else ""
        if self.query_one("#auto", Checkbox).value:
            flags += "/AUTO"
        if self.active:
            flags += " · AI…"
        elif self.proposal:
            flags += " · review F8"
        dirty = " *" if self.document.dirty else ""
        self.query_one("#masthead", Static).update(
            f" AIVim · {self.document.name}{dirty}   {mode} {row+1}:{col+1}{flags}"
        )

    def context_for(self, doc, start, end):
        selected = set(self.query_one("#source-list", SelectionList).selected)
        data = {
            "sources": [
                {"id": s.id, "name": s.name, "content": s.content}
                for s in self.sources
                if s.id in selected
            ]
        }
        if self.query_one("#nearby", Checkbox).value:
            data["nearby"] = {
                "before": doc.content[max(0, start - 2000) : start],
                "after": doc.content[end : end + 2000],
            }
        return json.dumps(data, ensure_ascii=False, indent=2)

    def update_context(self):
        count = len(self.query_one("#source-list", SelectionList).selected)
        self.query_one("#ai-details", Collapsible).title = f"Model & {count} sources"
        self.query_one("#context-count", Static).update(
            f"{count} sources · {len(self.context_for(self.document, *sorted(offset(self.editor.text, loc) for loc in self.editor.selection)).encode())}/51200 context bytes"
        )
        provider = self.query_one("#provider", Select).value
        if isinstance(provider, str):
            self.query_one("#ai-panel").border_title = "AI · " + self.service.models()[provider]
            available = self.service.is_model_configured(provider)
            self.query_one("#model-name", Static).update(
                self.service.models()[provider] + ("" if available else " · not configured")
            )

    @on(Select.Changed, "#documents")
    def document_selected(self, event: Select.Changed):
        if (
            isinstance(event.value, str)
            and event.value == event.select.value
            and event.value != self.current_id
        ):
            self.switch_document(event.value)

    @on(Select.Changed, "#provider")
    def provider_selected(self):
        if self.is_mounted:
            self.update_context()

    @on(SelectionList.SelectedChanged, "#source-list")
    def sources_changed(self):
        self.update_context()

    @on(SelectionList.SelectionHighlighted, "#source-list")
    def source_highlighted(self, event):
        for source in self.sources:
            if source.id == event.selection.value:
                self.query_one("#source-preview", TextArea).load_text(
                    source.name + "\n\n" + source.content
                )
                break

    def add_source(self, name, content):
        if len(self.sources) >= 30 or len(content.encode()) > 50 * 1024:
            self.say("Sources are limited to 30 snapshots, 50 KiB each.")
            return
        source = Source(name, content)
        self.sources.append(source)
        self.query_one("#source-list", SelectionList).add_option((name, source.id, True))
        self.update_context()
        self.say("Source added. Checked snapshots are included in the next request.")

    def source_file(self, path):
        if not path:
            return
        try:
            if Path(path).expanduser().stat().st_size > 50 * 1024:
                self.say("Source file exceeds 50 KiB.")
                return
            result = self.store.load(path)
        except (OSError, ValueError):
            self.say("Cannot read source file.")
            return
        if result:
            self.add_source(Path(path).name, result.content)
            if self.sources: self.sources[-1].path = str(Path(path).expanduser().resolve())
        else:
            self.say(result.message)

    def add_note(self, value):
        if value:
            self.add_source(*value)

    def get_system_commands(self, screen):
        yield from super().get_system_commands(screen)
        for title, help_text, callback in [
            ("Save model profile", "Name the current connection", self.action_save_profile),
            ("Model profiles", "Choose a saved model connection", self.action_model_profiles),
            ('Find', 'Search in document', self.action_find),
            ('Replace', 'Replace all literal occurrences', self.action_replace),
            ('Go to line', 'Jump to a line', self.action_goto),
            ('File picker', 'Browse project files', self.action_file_picker),
            ('Indentation', 'Spaces or tabs', self.action_indent_settings),
            ('Blocks', 'Inspect retry or cancel individual blocks', self.action_blocks),
            ('Source freshness', 'Check changed source files', self.action_source_status),
            ('Refresh sources', 'Reload source snapshots explicitly', self.action_refresh_sources),
            ('Check syntax', 'Validate without executing code', self.action_validate),
            ('Edit proposal', 'Adjust generated text before accepting', self.action_edit_proposal),
            ('Test model connection', 'Test selected model and show active route', self.action_model_status),
            ('Writing effect', 'Toggle live ink animation', self.action_writing_effect),
            ('Remember AI history', 'Opt in or out of persistent prompts and context', self.action_remember_history),
            ('Clear AI history', 'Delete saved prompts and responses', self.action_forget_history),

            ("Workspace menu", "Files, sources and live controls", self.action_workspace_menu),
            ("Files and buffers", "Open, save and switch documents", self.file_menu),
            ("Auto replace", "Toggle automatic completed live-block replacement", self.toggle_auto),
            ("View controls", "Pin, collapse and minimal view options", self.view_menu),
            ("New buffer", "Create an empty document", self.action_new),
            ("New with AI", "Generate a new document from natural language", self.action_new_ai),
            (
                "Connect HTTPS model",
                "Configure an OpenShift or OpenAI-compatible API",
                self.action_connect_model,
            ),
            ("Open file", "Open a text file", self.action_open),
            ("Save file", "Save the current buffer to disk", self.action_save),
            ("Sources", "Choose context snapshots for AI", self.action_sources),
            ("Selection actions", "Open the context menu", self.action_context_menu),
            ("Vim / standard keys", "Toggle modal keys or familiar typing", self.action_toggle_vim),
            ("Live generation", "Toggle blank-line instruction blocks", self.action_toggle_live),
            ("Cancel generation", "Cancel active AI work and the queue", self.cancel_ai),
        ]:
            yield SystemCommand(title, help_text, callback)

    def update_sidebar(self):
        workbench = self.query_one("#workbench")
        workbench.set_class(self.sidebar_visible, "show-ai")
        workbench.set_class(self.sidebar_pinned, "pinned")
        panel = self.query_one("#ai-panel")
        panel.styles.offset = (0, 0) if self.sidebar_pinned else (max(0, self.size.width - 50), 1)
        panel.styles.height = (
            "1fr" if self.sidebar_pinned else min(29, max(14, self.size.height - 4))
        )
        self.query_one("#pin-ai", Button).label = "Unpin" if self.sidebar_pinned else "Pin"
        self.query_one("#ai-toggle", Button).variant = (
            "primary" if self.sidebar_visible else "default"
        )

    def focus_ai_prompt(self):
        self._ai_focus_requested = True
        self.query_one("#workspace-tabs", TabbedContent).active = "editor-tab"
        self.reveal_ai()
        self.call_after_refresh(self.query_one("#instruction", TextArea).focus)

    def reveal_ai(self):
        self.sidebar_visible = True
        self.update_sidebar()

    def action_pin_ai(self):
        self.sidebar_pinned = not self.sidebar_pinned
        self.sidebar_visible = True
        self.update_sidebar()

    def collapse_ai(self):
        self.sidebar_pinned = False
        self.sidebar_visible = False
        self.update_sidebar()
        if self.current_id:
            self.editor.focus()

    def action_toggle_ai(self):
        if self.sidebar_visible:
            self.collapse_ai()
        else:
            self.focus_ai_prompt()

    def auto_hide_sidebar(self):
        if not self.sidebar_pinned and self.sidebar_visible:
            self.sidebar_visible = False
            self.update_sidebar()

    def on_descendant_focus(self, event: events.DescendantFocus):
        if event.widget.id == "instruction":
            self._ai_focus_requested = False
        elif self._ai_focus_requested:
            return
        if (
            isinstance(event.widget, EditorArea)
            and not self.sidebar_pinned
            and self.sidebar_visible
        ):
            self.sidebar_visible = False
            self.update_sidebar()

    def action_editor(self):
        self._ai_focus_requested = False
        self.query_one("#workspace-tabs", TabbedContent).active = "editor-tab"
        if not self.sidebar_pinned:
            self.sidebar_visible = False
            self.update_sidebar()
        if self.current_id:
            self.editor.focus()

    def action_connect_model(self):
        if self.active or self.pending:
            self.say("Finish or cancel current AI work before changing model connections.")
            return
        self.push_screen(
            ConnectionDialog(self.settings, self.service.credentials), self.connection_saved
        )

    def connection_saved(self, connection):
        if connection is None:
            return
        from .compatible import save_connection

        try:
            token = save_connection(self.settings, connection)
        except (ValueError, OSError) as exc:
            self.say("Connection was not saved: " + str(exc))
            return
        credentials = dict(self.service.credentials)
        if token:
            credentials["compatible"] = token
        self.service = AIService(
            settings=self.settings, credentials=credentials, endpoints=self.service.endpoints
        )
        self.query_one("#provider", Select).value = "compatible"
        self.update_context()
        self.focus_ai_prompt()
        self.say(
            "HTTPS model saved and selected. Ask AI to start; certificate verification is enabled."
        )

    def action_sources(self):
        self.query_one("#workspace-tabs", TabbedContent).active = "sources-tab"
        self.query_one("#source-list").focus()

    def action_history(self):
        self.query_one("#workspace-tabs", TabbedContent).active = "history-tab"

    def action_help(self):
        self.push_screen(TextDialog("AIVIM // FIELD MANUAL", HELP))

    def action_workspace_menu(self):
        choices = [
            ("editor", "Editor  [Alt+1]"),
            ("files", "Files & buffers…"),
            ("ai", "AI actions…  [F2]"),
            ("sources", "Sources  [F3]"),
            ("history", "History  [Alt+3]"),
            ("blocks", "Blocks · retry / cancel…"),
            ("find", "Find / search…  [Ctrl+F]"),
            ("validate", "Check syntax…"),
            (
                "live",
                "Live blocks: "
                + ("on" if self.query_one("#live", Checkbox).value else "off")
                + "  [F9]",
            ),
            (
                "auto",
                "Auto replace: " + ("on" if self.query_one("#auto", Checkbox).value else "off"),
            ),
            ("connect", "Connect HTTPS model…"),
            ("view", "View & keys…"),
            ("help", "Help  [F1]"),
            ("quit", "Quit  [F10]"),
        ]

        def chosen(value):
            actions = {
                "editor": self.action_editor,
                "files": self.file_menu,
                "ai": self.action_context_menu,
                "sources": self.action_sources,
                "history": self.action_history,
                "blocks": self.action_blocks,
                "find": self.action_find,
                "validate": self.action_validate,
                "live": self.action_toggle_live,
                "auto": self.toggle_auto,
                "connect": self.action_connect_model,
                "view": self.view_menu,
                "help": self.action_help,
                "quit": self.action_quit,
            }
            if value in actions:
                actions[value]()

        self.push_screen(ChoiceDialog("AIVIM", choices, x=0, y=1), chosen)

    def toggle_auto(self):
        box = self.query_one("#auto", Checkbox)
        box.value = not box.value
        self.say("Auto replace " + ("on" if box.value else "off"))

    def file_menu(self):
        choices = [
            ("new", "New  [Ctrl+N]"),
            ("ai", "New with AI"),
            ("browse", "Browse files…"),
            ("open", "Open…  [Ctrl+O]"),
            ("save", "Save  [Ctrl+S]"),
            ("saveas", "Save as…"),
            ("buffers", "Switch buffer…"),
            ("close", "Close  [Ctrl+W]"),
        ]

        def chosen(value):
            if value == "new":
                self.run_worker(self.action_new())
            elif value == "ai":
                self.run_worker(self.action_new_ai())
            elif value == "browse":
                self.action_file_picker()
            elif value == "open":
                self.action_open()
            elif value == "save":
                self.action_save()
            elif value == "saveas":
                doc = self.document
                self.push_screen(
                    PromptDialog("Save as", value=doc.name),
                    lambda path: self.save_document(doc, path) if path else None,
                )
            elif value == "buffers":
                self.push_screen(
                    ChoiceDialog(
                        "BUFFERS",
                        [
                            (doc.id, ("* " if doc.dirty else "") + doc.name)
                            for doc in self.documents.values()
                        ],
                    ),
                    lambda key: self.switch_document(key) if key else None,
                )
            elif value == "close":
                self.action_close_document()

        self.push_screen(ChoiceDialog("FILES", choices, x=1, y=2), chosen)

    def view_menu(self):
        choices = [
            ("pin", ("Unpin" if self.sidebar_pinned else "Pin") + " AI Workbench"),
            ("collapse", "Collapse AI"),
            ("numbers", "Toggle line numbers"),
            ("keys", "Toggle shortcut bar"),
            ("vim", "Vim / standard keys  [F4]"),
        ]

        def chosen(value):
            if value == "pin":
                self.action_pin_ai()
            elif value == "collapse":
                self.collapse_ai()
            elif value == "numbers":
                self.line_numbers = not self.line_numbers
                for area in self.areas.values():
                    area.show_line_numbers = self.line_numbers
            elif value == "keys":
                self.default_screen.toggle_class("show-shortcuts")
            elif value == "vim":
                self.action_toggle_vim()

        self.push_screen(ChoiceDialog("VIEW", choices, x=1, y=2), chosen)

    def action_context_menu(self):
        if self.current_id:
            self.show_context_menu(self.editor)

    @on(EditorArea.ContextRequested)
    def context_requested(self, event: EditorArea.ContextRequested):
        self.show_context_menu(event.area, event.x, event.y)

    def show_context_menu(self, area, x=None, y=None):
        self.switch_document(area.id.removeprefix("doc-"))
        title = (
            f"SELECTION // {len(area.selected_text)} characters"
            if area.selected_text
            else "CURSOR // create something new"
        )
        choices = [
            ("query", "Ask about selection"),
            ("improve", "Rewrite selection  [F7]"),
            ("explain", "Explain selection  [F6]"),
            ("analyze", "Analyze selection"),
            ("generate", "Generate at cursor  [F5]"),
            ("context", "Inspect AI context"),
            ("source", "Selection → source note"),
        ]

        def chosen(action):
            if action == "context":
                self.show_context()
            elif action == "source":
                if area.selected_text:
                    self.add_source(self.document.name + " selection", area.selected_text)
                else:
                    self.say("Select text to add a source note.")
            elif action:
                self.query_one("#ai-action", Select).value = action
                if action in ("query", "generate", "improve"):
                    self.focus_ai_prompt()
                    self.say("Enter an instruction, then Ask AI. Selection is preserved.")
                else:
                    self.submit_action(action)

        self.push_screen(ChoiceDialog(title, choices, x=x, y=y), chosen)

    def show_context(self):
        self._sync_document(self.editor)
        a, b = sorted(offset(self.document.content, loc) for loc in self.editor.selection)
        self.push_screen(
            TextDialog("EXACT CONTEXT // next request", self.context_for(self.document, a, b))
        )

    def action_toggle_vim(self):
        self.vim_enabled = not self.vim_enabled
        for area in self.areas.values():
            area.vim_enabled = self.vim_enabled
            area.set_mode("NORMAL" if self.vim_enabled else "STANDARD")
        self.update_selection()
        self.say(
            "Vim keys enabled: i inserts, Esc returns to Normal."
            if self.vim_enabled
            else "Standard editing: type normally; drag or Shift+arrows to select."
        )
        self.editor.focus()

    def action_toggle_live(self):
        box = self.query_one("#live", Checkbox)
        box.value = not box.value

    @on(Checkbox.Changed, "#live")
    def live_changed(self, event: Checkbox.Changed):
        if not self.current_id:
            return
        if event.value:
            self._sync_document(self.editor)
            row, _ = self.editor.cursor_location
            self.document.live_from = offset(self.document.content, (row, 0))
            self.say("LIVE armed on this line. Enter twice submits; keep typing the next block.")
        else:
            for doc in self.documents.values():
                doc.live_from = None
            self.pending.clear()
            if self.active and self.active.live:
                self.cancel_ai()
            self.say("Live generation off.")
        self.update_live_hint()

    def prepare_live_edit(self, area):
        if not self.query_one("#live", Checkbox).value or not area.selection.is_empty:
            return
        self._sync_document(area)
        doc = self.documents[area.id.removeprefix("doc-")]
        row, _ = area.cursor_location
        line_start = offset(doc.content, (row, 0))
        head = offset(doc.content, area.cursor_location)
        if not area.document.get_line(row).strip() and (
            doc.live_from is None
            or head < doc.live_from
            or not doc.content[doc.live_from : head].strip()
        ):
            doc.live_from = line_start

    @on(EditorArea.BlockBoundary)
    def block_boundary(self, event: EditorArea.BlockBoundary):
        self.handle_live_boundary(event.area)

    def handle_live_boundary(self, area):
        self._sync_document(area)
        if not self.query_one("#live", Checkbox).value:
            return
        doc = self.documents[area.id.removeprefix("doc-")]
        head = offset(doc.content, area.cursor_location)
        block = completed_block(doc.content, doc.live_from, head)
        if not block:
            return
        if len(self.pending) >= 10:
            self.say("Live queue is full; submit the remaining instruction manually.")
            return
        start, end, instruction = block
        request = self.make_request(doc, start, end, "generate", instruction, live=True)
        if request:
            doc.live_from = head
            self.pending.append(request)
            self.pump()
            self.update_live_hint()

    @on(Checkbox.Changed, "#auto")
    def auto_changed(self, event: Checkbox.Changed):
        if event.value:
            for request in [self.active, self.proposal, *self.pending]:
                if request and request.live:
                    request.auto = True
            if self.proposal and self.proposal.live:
                self.action_accept()
        self.update_live_hint()

    def update_live_hint(self):
        if not self.current_id:
            return
        if not self.query_one("#live", Checkbox).value:
            hint = "LIVE OFF · F9 enables blank-line instruction blocks"
        elif self.active:
            hint = f"LIVE · generating · {len(self.pending)} queued · keep typing"
        elif self.proposal:
            hint = f"LIVE · review pending: F8 accept / Reject · {len(self.pending)} queued"
        else:
            hint = "LIVE · ready for the next instruction · blank line submits"
        self.query_one("#live-hint", Static).update(hint)
        self.update_titlebar()

    def make_request(self, doc, start, end, action, instruction, *, live=False):
        provider = self.query_one("#provider", Select).value
        if not self.service.is_model_configured(provider):
            self.say(
                "Provider is not configured. Set its API credential or choose a configured provider."
            )
            return None
        if action in ("improve", "explain", "analyze") and start == end:
            self.say("Select text with mouse or v/V before this action.")
            return None
        if action in ("query", "generate") and not instruction.strip():
            self.say("Describe what you want in the AI instruction field.")
            return None
        context = self.context_for(doc, start, end)
        if (
            len(doc.content[start:end].encode()) > 50 * 1024
            or len(context.encode()) > 50 * 1024
            or len(instruction.encode()) > 8 * 1024
        ):
            self.say(
                "AI limit: 50 KiB selection/context, 8 KiB instruction. Reduce the selection or checked sources."
            )
            return None
        return Request(
            doc.id,
            start,
            end,
            doc.content[start:end],
            action,
            instruction,
            context,
            provider,
            self.service.models()[provider],
            live=live,
            auto=live and self.query_one("#auto", Checkbox).value,
        )

    def action_submit(self):
        self.submit_action(self.query_one("#ai-action", Select).value)

    def action_generate(self):
        self.query_one("#workspace-tabs", TabbedContent).active = "editor-tab"
        self.query_one("#ai-action", Select).value = "generate"
        self.focus_ai_prompt()
        self.say("Describe the code or text to generate at the cursor, then Ask AI.")

    def action_explain(self):
        self.submit_action("explain")

    def action_rewrite(self):
        self.submit_action("improve")

    def submit_action(self, action):
        if self.active:
            self.say("AI is working. Keep editing, or cancel before another manual request.")
            return
        self._sync_document(self.editor)
        doc = self.document
        start, end = sorted(offset(doc.content, loc) for loc in self.editor.selection)
        if action == "generate":
            start = end = offset(doc.content, self.editor.cursor_location)
        instruction = self.query_one("#instruction", TextArea).text
        request = self.make_request(doc, start, end, action, instruction)
        if request:
            self.start_request(request)

    def pump(self):
        if self.active or self.proposal:
            return
        while self.pending:
            request = self.pending.pop(0)
            if not request.invalid and request.document_id in self.documents:
                self.start_request(request)
                break

    def start_request(self, request):
        if self.proposal:
            self.proposal.state = "Superseded"
            self.clear_proposal()
        doc = self.documents[request.document_id]
        self._sync_document(self.areas[doc.id])
        request.original = doc.content[request.start : request.end]
        request.job = AIJob(
            doc.id,
            0,
            doc.content,
            request.action,
            request.provider,
            request.model,
            ((request.start, request.end),),
            request.context,
            request.instruction,
            time.monotonic() + self.settings.ai.timeout,
            request_id=request.id,
            cancellation=request.cancel,
        )
        request.state = "Generating"
        self.active = request
        if request.live and self.writing_effect:
            area = self.areas[request.document_id]
            area.ink_request, area.ink_text = request, "Composing…"
            area.refresh()
        self.records.insert(0, request)
        self.records = self.records[:50]
        self.raw_preview = ""
        self.query_one("#result", TextArea).load_text("Connecting to " + request.provider + "…")
        self.query_one("#submit", Button).disabled = True
        self.query_one("#cancel", Button).disabled = False
        if not request.live:
            self.focus_ai_prompt()
        self.say("Generating. Your editor remains active; F2 opens actions.")
        self.render_history()

        def publish(kind, value):
            while not request.cancel.is_set():
                try:
                    self.mailbox.put((request.id, kind, value), timeout=0.05)
                    return
                except queue.Full:
                    pass
            raise AIError("CANCELLED", "Request cancelled")

        def worker():
            try:
                snapshot = request.job.source_snapshot
                code = (
                    ""
                    if request.action == "generate"
                    else snapshot[
                        request.job.selected_ranges[0][0] : request.job.selected_ranges[0][1]
                    ]
                )
                instruction = request.instruction
                if request.action == "generate":
                    language = self.areas[doc.id].language or "plain text"
                    instruction = "Requested output language: " + language + "\n" + instruction
                result = self.service.request(
                    request.action,
                    code,
                    request.context,
                    instruction,
                    provider=request.provider,
                    model=request.model,
                    request_id=request.id,
                    cancel=request.cancel,
                    on_delta=lambda delta: publish("delta", delta),
                )
                publish("done", result)
            except AIError as exc:
                if not request.cancel.is_set():
                    publish("error", str(exc))
            except Exception:
                if not request.cancel.is_set():
                    publish("error", "AI request failed; input preserved.")

        threading.Thread(target=worker, daemon=True, name="aivim-tui-ai").start()

    def drain_ai(self):
        if self._workspace_closing:
            return
        for area in self.areas.values():
            if area.ink_request: area.refresh()
        if self.proposal and self.proposal.live and self.proposal.auto and self._ink_ready_at and time.monotonic() >= self._ink_ready_at:
            self._ink_ready_at = 0
            if self.query_one("#live", Checkbox).value and self.query_one("#auto", Checkbox).value: self.action_accept()
        for _ in range(128):
            try:
                request_id, kind, value = self.mailbox.get_nowait()
            except queue.Empty:
                break
            request = self.active
            if not request or request.id != request_id or request.cancel.is_set():
                continue
            if kind == "delta":
                self.raw_preview += value
                preview = (
                    partial_code(self.raw_preview)
                    if request.action in ("improve", "generate")
                    else self.raw_preview
                )
                self.query_one("#result", TextArea).load_text(preview)
                area = self.areas.get(request.document_id)
                if area and request.live and self.writing_effect and not request.invalid:
                    area.ink_request, area.ink_text = request, preview
                    area.refresh()
                continue
            self._sync_document(self.areas[request.document_id])
            self.active = None
            self.query_one("#submit", Button).disabled = False
            self.query_one("#cancel", Button).disabled = True
            if kind == "error":
                request.state = "Failed"
                request.result = value
                self.say(value)
            elif request.action in ("improve", "generate"):
                try:
                    proposal = parse_proposal(request.job, value)
                    request.result = proposal.explanation + "\n\n" + "\n".join(proposal.diff())
                    self.query_one("#result", TextArea).load_text(request.result)
                    if request.invalid:
                        request.state = "Stale"
                        self.say(
                            "Stale result: instruction or selection changed. Your text is preserved."
                        )
                    else:
                        request.replacement = proposal.edits[0].text
                        request.state = "Awaiting review"
                        self.proposal = request
                        self.query_one("#accept", Button).disabled = False
                        self.query_one("#reject", Button).disabled = False
                        self.say(
                            "Proposal ready. F8 accepts one undoable change; Reject keeps your text."
                        )
                        if (
                            request.live
                            and request.auto
                            and self.query_one("#live", Checkbox).value
                            and self.query_one("#auto", Checkbox).value
                        ):
                            if self.writing_effect:
                                self._ink_ready_at = time.monotonic() + 0.22
                            else: self.action_accept()
                except AIError as exc:
                    request.state = "Failed"
                    request.result = str(exc)
                    self.say(str(exc))
            else:
                request.state = "Answered"
                request.result = value.text
                self.query_one("#result", TextArea).load_text(value.text)
                self.say("Response ready. Document unchanged.")
            self.render_history()
            self.pump()
            self.update_live_hint()

    def clear_proposal(self):
        self.proposal = None
        self._ink_ready_at = 0
        for area in self.areas.values(): area.ink_request = None; area.refresh()
        self.query_one("#accept", Button).disabled = True
        self.query_one("#reject", Button).disabled = True

    def action_accept(self):
        request = self.proposal
        if not request:
            return
        area = self.areas.get(request.document_id)
        if area:
            self._sync_document(area)
        doc = self.documents.get(request.document_id)
        if (
            not doc
            or request.invalid
            or doc.content[request.start : request.end] != request.original
        ):
            request.state = "Stale"
            self.clear_proposal()
            self.render_history()
            self.say("Stale result. Your text is preserved.")
            return
        self.clear_proposal()
        area.history.checkpoint()
        area.replace(
            request.replacement,
            location(doc.content, request.start),
            location(doc.content, request.end),
            maintain_selection_offset=True,
        )
        area.history.checkpoint()
        self._sync_document(area)
        request.state = "Accepted"
        self.render_history()
        self.say("Accepted. Undo restores the original instruction or selection.")
        if not request.live and not self.sidebar_pinned:
            self.auto_hide_sidebar()
            self.editor.focus()
        self.pump()
        self.update_live_hint()

    def cancel_ai(self):
        self.pending.clear()
        for area in self.areas.values(): area.ink_request = None; area.refresh()
        if self.active:
            self.active.cancel.set()
            self.active.state = "Cancelled"
            self.active = None
        self.query_one("#submit", Button).disabled = False
        self.query_one("#cancel", Button).disabled = True
        self.render_history()
        self.say("Cancelled. Input preserved; waiting blocks cleared.")
        self.update_live_hint()

    def render_history(self):
        log = self.query_one("#history-log", RichLog)
        log.clear()
        for record in reversed(self.records):
            name = (
                self.documents[record.document_id].name
                if record.document_id in self.documents
                else "closed buffer"
            )
            log.write(
                f"── {record.action.upper()} / {record.provider} / {name} / {record.state} ──"
            )
            log.write("Instruction: " + (record.instruction or "(selection action)"))
            log.write("Target snapshot:\n" + record.original)
            log.write("Context snapshot:\n" + record.context)
            if record.result:
                log.write(record.result)
            log.write("")

    def action_redo(self):
        target = self.focused if isinstance(self.focused, TextArea) else self.editor
        if not target.read_only:
            target.redo()

    async def action_new(self):
        await self.new_document()
        self.action_editor()

    async def action_new_ai(self):
        await self.action_new()
        self.action_generate()

    def action_open(self):
        self.push_screen(
            PromptDialog("Open a UTF-8 text file", placeholder="~/project/file.py"),
            self.open_from_prompt,
        )

    async def open_from_prompt(self, value):
        if value and value.strip():
            if await self.open_document(value):
                self.action_editor()

    def save_document(self, doc, path=None, *, force=False):
        self._sync_document(self.areas[doc.id])
        path = path or (doc.identity.target if doc.identity else None)
        if not path:
            return False
        result = self.store.save(
            path,
            doc.content,
            doc.identity,
            force=force,
            backup_dir=self.settings.file.backup_dir if self.settings.file.auto_backup else None,
        )
        if not result:
            self.say(result.message)
            return False
        doc.identity = result.identity
        doc.name = Path(path).name
        doc.saved = doc.content
        self.refresh_documents()
        self.say("Saved " + doc.name)
        return True

    def action_save(self):
        doc = self.document
        if doc.identity:
            self.save_document(doc)
        else:
            self.push_screen(
                PromptDialog("Save buffer as", value=doc.name),
                lambda path: self.save_document(doc, path) if path else None,
            )

    def action_command(self):
        self.push_screen(
            PromptDialog("Vim command", placeholder="w / w! / w path / wq / q / e path"),
            self.execute_command,
        )

    async def execute_command(self, value):
        if not value:
            return
        command, _, argument = value.lstrip(":").strip().partition(" ")
        if command.isdigit():
            self.goto_line(command)
        elif command in ("w", "w!", "saveas"):
            if argument:
                self.save_document(self.document, argument, force=command == "w!")
            elif self.document.identity:
                self.save_document(self.document, force=command == "w!")
            else:
                self.action_save()
        elif command == "wq":
            if self.document.identity and self.save_document(self.document):
                self.action_quit()
            elif not self.document.identity:
                doc = self.document

                def saved(path):
                    if path and self.save_document(doc, path):
                        self.action_quit()

                self.push_screen(PromptDialog("Save before quitting", value=doc.name), saved)
        elif command == "q":
            self.action_quit()
        elif command == "q!":
            self.finish_exit()
        elif command in ("e", "edit") and argument:
            await self.open_document(argument)
        elif command == "new":
            await self.action_new()
        elif command in ("tabnext", "tabprev"):
            ids = list(self.documents)
            self.switch_document(
                ids[(ids.index(self.current_id) + (1 if command == "tabnext" else -1)) % len(ids)]
            )
        else:
            self.say("Unknown command. F1 lists supported commands.")

    def action_quit(self):
        if len(self.screen_stack) > 1:
            return
        for area in self.areas.values():
            self._sync_document(area)
        if any(d.dirty for d in self.documents.values()):
            self.push_screen(
                ChoiceDialog(
                    "UNSAVED BUFFERS // keep your work",
                    [
                        ("save", "Save all and quit"),
                        ("discard", "Discard unsaved changes and quit"),
                    ],
                ),
                self.quit_choice,
            )
        else:
            self.finish_exit()

    def quit_choice(self, choice):
        if choice == "discard":
            self.finish_exit()
        elif choice == "save":
            self.save_next_for_exit()

    def save_next_for_exit(self):
        doc = next((d for d in self.documents.values() if d.dirty), None)
        if not doc:
            self.finish_exit()
        elif doc.identity:
            if self.save_document(doc):
                self.save_next_for_exit()
        else:

            def saved(path):
                if path and self.save_document(doc, path):
                    self.save_next_for_exit()

            self.push_screen(
                PromptDialog("Save " + doc.name + " before quitting", value=doc.name), saved
            )

    def finish_exit(self):
        self.snapshot_session()
        self._workspace_closing = True
        if self.active:
            self.active.cancel.set()
        self.exit()

    def on_unmount(self):
        self.snapshot_session()
        self._workspace_closing = True
        if self.active:
            self.active.cancel.set()

    def action_close_document(self):
        doc = self.document
        self._sync_document(self.editor)
        if doc.dirty:
            self.push_screen(
                ChoiceDialog(
                    "Close " + doc.name + "?",
                    [("save", "Save and close"), ("discard", "Discard changes and close")],
                ),
                lambda choice: self.close_choice(doc, choice),
            )
        else:
            self.run_worker(self.remove_document(doc.id))

    def close_choice(self, doc, choice):
        if choice == "discard":
            self.run_worker(self.remove_document(doc.id))
        elif choice == "save":

            def saved(path):
                if path and self.save_document(doc, path):
                    self.run_worker(self.remove_document(doc.id))

            if doc.identity:
                saved(doc.identity.target)
            else:
                self.push_screen(PromptDialog("Save before closing", value=doc.name), saved)

    async def remove_document(self, document_id):
        if self.active and self.active.document_id == document_id:
            self.cancel_ai()
        self.pending = [r for r in self.pending if r.document_id != document_id]
        if self.proposal and self.proposal.document_id == document_id:
            self.proposal.state = "Closed"
            self.clear_proposal()
        area = self.areas.pop(document_id)
        self.documents.pop(document_id)
        if self.current_id == document_id:
            self.current_id = next(iter(self.documents), None)
        await area.remove()
        if self.documents:
            self.switch_document(next(iter(self.documents)))
            self.refresh_documents()
        else:
            self.current_id = None
            await self.new_document()
        self.render_history()

    @on(Button.Pressed)
    async def button_pressed(self, event: Button.Pressed):
        button = event.button.id
        actions = {
            "main-menu": self.action_workspace_menu,
            "save": self.action_save,
            "open": self.action_open,
            "close": self.action_close_document,
            "actions": self.action_context_menu,
            "vim": self.action_toggle_vim,
            "redo": self.action_redo,
            "submit": self.action_submit,
            "cancel": self.cancel_ai,
            "context": self.show_context,
            "accept": self.action_accept,
            "ai-toggle": self.action_toggle_ai,
            "hide-ai": self.collapse_ai,
            "pin-ai": self.action_pin_ai,
            "connect-model": self.action_connect_model,
        }
        if button in actions:
            actions[button]()
        elif button == "new":
            await self.action_new()
        elif button == "new-ai":
            await self.action_new_ai()
        elif button == "undo":
            self.editor.undo()
        elif button == "reject":
            if self.proposal:
                self.proposal.state = "Rejected"
                self.clear_proposal()
                self.render_history()
                self.say("Rejected. Your text is unchanged.")
                self.pump()
        elif button == "source-file":
            self.push_screen(
                PromptDialog("Add a source file", placeholder="~/project/reference.md"),
                self.source_file,
            )
        elif button == "source-note":
            self.push_screen(NoteDialog(), self.add_note)
        elif button == "source-buffer":
            self._sync_document(self.editor)
            self.add_source(self.document.name, self.document.content)
        elif button == "source-remove":
            listing = self.query_one("#source-list", SelectionList)
            index = listing.highlighted
            if index is not None:
                source = self.sources.pop(index)
                listing.remove_option_at_index(index)
                self.query_one("#source-preview", TextArea).load_text("Source removed.")
                self.update_context()
