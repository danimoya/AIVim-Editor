"""Headless terminal event-loop journeys, through real UI events and SDK streams."""

import asyncio
import json
from pathlib import Path
import time

from textual.widgets import TextArea, Select, SelectionList, Checkbox, Static
from textual.widgets.text_area import Selection

from aivim.tui import TerminalWorkspace
from aivim.tui_widgets import ChoiceDialog, PromptDialog
from aivim.tui_model import completed_block, partial_code, Request, map_request
from provider_stub import ProviderStub
from test_ai_jobs import service


async def settle(pilot, predicate, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        await pilot.pause(0.04)
        if predicate():
            return
    assert predicate(), "Timed out waiting for terminal workspace"


def test_retro_editor_vim_mouse_context_tooltips_and_resize(settings, tmp_path):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(132, 46)) as pilot:
            await pilot.press("i", "A", "é", "界", "escape")
            assert app.editor.text == "Aé界" and app.editor.mode == "NORMAL"
            await pilot.press("g", "g", "v", "l")
            selected = app.editor.selected_text
            assert selected == "Aé"
            await pilot.click(app.editor, offset=(7, 2), button=3)
            assert isinstance(app.screen, ChoiceDialog) and app.editor.selected_text == selected
            await pilot.press("escape", "f2")
            assert isinstance(app.screen, ChoiceDialog)
            await pilot.press("escape", "escape", "g", "g", "y", "y", "p")
            assert app.editor.text == "Aé界\nAé界"
            await pilot.press("u")
            assert app.editor.text == "Aé界"
            await pilot.press("f4")
            assert not app.editor.vim_enabled
            app.editor.move_cursor((0, 3))
            await pilot.press("!")
            assert app.editor.text == "Aé界!"
            assert app.query_one("#actions").tooltip
            await pilot.resize_terminal(80, 40)
            await pilot.pause()
            assert app.query_one("#workbench").has_class("narrow")
            assert app.query_one("#submit").region.right <= 80
            await pilot.resize_terminal(132, 46)
            await pilot.pause()
            app.save_screenshot(str(tmp_path / "terminal-workspace.svg"))

    asyncio.run(journey())


def test_terminal_sources_stream_review_undo_and_document_ownership(settings):
    async def journey(stub):
        stub.text = json.dumps({"code": "return 2", "explanation": "Use two"})
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(132, 46)) as pilot:
            app.editor.load_text("# 😀 keep\nreturn 1\n# tail")
            await pilot.pause()
            app.add_source("Style", "Return integers")
            app.add_source("Design", "Pure functions")
            app.add_source("Private", "DO_NOT_SEND")
            listing = app.query_one("#source-list", SelectionList)
            listing.deselect(app.sources[-1].id)
            app.editor.selection = Selection((1, 0), (1, 8))
            app.query_one("#instruction", TextArea).load_text("Use two instead")
            app.action_rewrite()
            await settle(pilot, lambda: app.proposal is not None)
            prompt = json.loads(stub.calls[-1][1]["messages"][-1]["content"])
            assert prompt["source"] == "return 1" and prompt["instruction"] == "Use two instead"
            assert (
                "Return integers" in prompt["context"]
                and "Pure functions" in prompt["context"]
                and "DO_NOT_SEND" not in prompt["context"]
            )
            assert app.editor.text == "# 😀 keep\nreturn 1\n# tail"
            origin = app.current_id
            await app.new_document(content="other buffer")
            app.action_accept()
            await pilot.pause()
            assert (
                app.editor.text == "other buffer"
                and app.areas[origin].text == "# 😀 keep\nreturn 2\n# tail"
            )
            app.switch_document(origin)
            app.editor.undo()
            await pilot.pause()
            assert app.editor.text == "# 😀 keep\nreturn 1\n# tail"
            assert app.records[0].state == "Accepted"

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_terminal_live_block_queue_stale_and_cancel(settings):
    async def journey(stub):
        stub.text = json.dumps({"code": "print(2)", "explanation": "Generated"})
        stub.chunk_delay = 0.03
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(132, 46)) as pilot:
            await pilot.press("f4")
            app.query_one("#live", Checkbox).value = True
            app.query_one("#auto", Checkbox).value = True
            await pilot.pause()
            app.editor.focus()
            await pilot.press(*"print two", "enter")
            assert not stub.calls
            await pilot.press(*"on the console", "enter", "enter")
            await settle(pilot, lambda: app.active is not None)
            await pilot.press(*"print two again", "enter", "enter")
            await settle(
                pilot,
                lambda: len(app.records) == 2 and all(r.state == "Accepted" for r in app.records),
                timeout=8,
            )
            assert app.editor.text.count("print(2)") == 2 and "again" not in app.editor.text
            app.editor.undo()
            await pilot.pause()
            assert "print two again" in app.editor.text
            await app.new_document()
            app.editor.focus()
            await pilot.press(*"print two", "enter", "enter")
            await settle(pilot, lambda: app.active is not None)
            app.editor.move_cursor((0, 0))
            await pilot.press(*"changed ")
            await settle(pilot, lambda: app.active is None)
            assert app.records[0].state == "Stale" and app.editor.text.startswith(
                "changed print two"
            )
            await app.new_document()
            app.editor.focus()
            await pilot.press(*"print two", "enter", "enter")
            await settle(pilot, lambda: app.active is not None)
            app.cancel_ai()
            await pilot.pause(0.4)
            assert app.records[0].state == "Cancelled" and "print two" in app.editor.text

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_terminal_safe_save_external_conflict_and_dirty_exit(settings, tmp_path):
    async def journey():
        path = tmp_path / "unicode.txt"
        path.write_bytes(b"\xef\xbb\xbfhello\r\n")
        app = TerminalWorkspace(str(path), settings=settings)
        async with app.run_test(size=(120, 40)) as pilot:
            app.editor.move_cursor((0, 5))
            await pilot.press("a", "界", "escape")
            assert app.save_document(app.document)
            assert path.read_bytes() == b"\xef\xbb\xbfhello\xe7\x95\x8c\r\n"
            path.write_text("external")
            await pilot.press("i", "X", "escape")
            assert not app.save_document(app.document) and path.read_text() == "external"
            assert app.document.dirty
            app.action_quit()
            await pilot.pause()
            assert isinstance(app.screen, ChoiceDialog)
            await pilot.press("escape")
            assert app.document.dirty
            assert app.save_document(app.document, force=True)
            app.action_quit()
            assert app._workspace_closing

    asyncio.run(journey())


def test_terminal_failed_stream_keeps_instruction(settings):
    async def journey(stub):
        stub.text = json.dumps({"code": "partial", "explanation": ""})
        stub.finish = "length"
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(120, 40)) as pilot:
            app.editor.load_text("original")
            await pilot.pause()
            app.editor.selection = Selection((0, 0), (0, 8))
            app.action_rewrite()
            await settle(pilot, lambda: app.active is None)
            assert (
                not app.proposal
                and app.editor.text == "original"
                and app.records[0].state == "Failed"
            )

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_terminal_block_and_anchor_helpers():
    assert completed_block("instruction\ncontinued\n", 0, 22) is None
    text = "instruction\ncontinued\n \n  "
    assert completed_block(text, 0, len(text))[2] == "instruction\ncontinued"
    assert partial_code('{"code":"print(\\"界\\")\\n') == 'print("界")\n'
    request = Request("doc", 4, 10, "target", "improve", "", "", "openai", "model")
    map_request(request, 0, 0, 2)
    assert (request.start, request.end, request.invalid) == (6, 12, False)
    map_request(request, 8, 8, 1)
    assert request.invalid


def test_repeated_instruction_anchor_and_outside_edit(settings):
    async def journey(stub):
        stub.text = json.dumps({"code": "changed", "explanation": "ok"})
        stub.delay = 0.15
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(132, 46)) as pilot:
            app.editor.load_text("same\n\nsame\n\n")
            await pilot.pause()
            app.editor.selection = Selection((0, 0), (0, 4))
            app.action_rewrite()
            app.editor.replace("", (0, 0), (2, 0))
            await settle(pilot, lambda: app.active is None)
            assert app.records[0].state == "Stale" and app.editor.text == "same\n\n"
            app.editor.selection = Selection((0, 0), (0, 4))
            app.action_rewrite()
            # An insertion after the target must not invalidate it.
            app.editor.insert("tail", location=(2, 0))
            await settle(pilot, lambda: app.proposal is not None)
            app.action_accept()
            await pilot.pause()
            assert app.editor.text == "changed\n\ntail"

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_terminal_compact_panel_note_and_palette(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(80, 24), tooltips=True) as pilot:
            assert app.query_one("#workbench").has_class("compact")
            assert app.editor.region.bottom <= app.size.height
            await pilot.press("f5")
            await pilot.pause()
            assert app.query_one("#workbench").has_class("show-ai")
            prompt = app.query_one("#instruction", TextArea)
            assert prompt.has_focus and prompt.region.y < 24 and prompt.region.bottom <= 24
            await pilot.press("alt+a")
            await pilot.pause()
            assert app.editor.has_focus
            await pilot.press("f3")
            await pilot.click("#source-note")
            await pilot.pause()
            from aivim.tui_widgets import NoteDialog

            assert isinstance(app.screen, NoteDialog)
            app.screen.query_one("#note-name").value = "Style guide"
            app.screen.query_one("#note-content", TextArea).load_text(
                "Short functions.\nExplicit types."
            )
            await pilot.click("#note-add")
            await pilot.pause()
            assert app.sources[0].content == "Short functions.\nExplicit types."
            assert any(c.title == "New with AI" for c in app.get_system_commands(app.screen))

    asyncio.run(journey())


def test_terminal_close_dirty_buffer_keeps_other_document(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(120, 40)) as pilot:
            app.editor.load_text("first")
            await pilot.pause()
            origin = app.current_id
            await app.new_document(content="second")
            await pilot.pause()
            app.action_close_document()
            await pilot.pause()
            assert isinstance(app.screen, ChoiceDialog)
            await pilot.click("#choice-discard")
            await pilot.pause()
            assert (
                app.current_id == origin and app.editor.text == "first" and len(app.documents) == 1
            )
            app.action_close_document()
            await pilot.pause()
            await pilot.click("#choice-discard")
            await pilot.pause()
            assert len(app.documents) == 1 and app.editor.text == ""

    asyncio.run(journey())


def test_sequential_live_blocks_with_normalized_generated_newlines(settings):
    async def journey(stub):
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(132, 44)) as pilot:
            await pilot.press("f4")
            app.query_one("#live", Checkbox).value = True
            app.query_one("#auto", Checkbox).value = True
            await pilot.pause()
            for number in range(3):
                app.editor.focus()
                # The editor normalizes CRLF, so anchors must use the actual inserted size.
                stub.text = json.dumps({"code": f"print({number})\r\n", "explanation": "new"})
                app.editor.insert(f"print number {number}")
                await pilot.press("enter", "enter")
                await settle(
                    pilot,
                    lambda: len(app.records) == number + 1 and app.records[0].state == "Accepted",
                )
                assert app.document.live_from == len(app.editor.text)
            assert len(stub.calls) == 3 and all(f"print({n})" in app.editor.text for n in range(3))
            # Starting a new instruction on an earlier blank line must re-arm it there.
            app.editor.move_cursor((1, 0))
            stub.text = json.dumps({"code": "print(99)", "explanation": "new"})
            await pilot.press(*"print ninety nine", "enter", "enter")
            await settle(
                pilot, lambda: len(app.records) == 4 and app.records[0].state == "Accepted"
            )
            assert "print(99)" in app.editor.text

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_enabling_auto_applies_waiting_live_proposal(settings):
    async def journey(stub):
        stub.text = json.dumps({"code": "print(2)", "explanation": "new"})
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(132, 44)) as pilot:
            await pilot.press("f4")
            app.query_one("#live", Checkbox).value = True
            await pilot.pause()
            app.editor.focus()
            await pilot.press(*"print two", "enter", "enter")
            await settle(pilot, lambda: app.proposal is not None)
            app.query_one("#auto", Checkbox).value = True
            await settle(pilot, lambda: app.records[0].state == "Accepted")
            app.editor.focus()
            await pilot.press(*"print two again", "enter", "enter")
            await settle(
                pilot, lambda: len(app.records) == 2 and app.records[0].state == "Accepted"
            )

    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_sidebar_auto_hide_pin_and_collapse(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(132, 44)) as pilot:
            assert not app.sidebar_visible and not app.query_one("#ai-panel").display
            await pilot.press("f5")
            await pilot.pause()
            assert app.sidebar_visible and app.query_one("#instruction", TextArea).has_focus
            await pilot.click("#pin-ai")
            await pilot.click(app.editor, offset=(5, 2))
            assert app.sidebar_pinned and app.sidebar_visible
            await pilot.click("#pin-ai")
            await pilot.click(app.editor, offset=(5, 2))
            assert not app.sidebar_visible
            await pilot.click("#ai-toggle")
            await pilot.pause()
            assert app.sidebar_visible
            await pilot.click("#hide-ai")
            await pilot.pause()
            assert not app.sidebar_visible and app.editor.has_focus

    asyncio.run(journey())


def test_minimal_editor_floating_panel_and_file_menu(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.editor.region.height == 22 and app.editor.region.width == 80
            assert app.editor.content_region.height == 22
            assert (
                not app.query_one("#file-bar").display
                and not app.query_one("#editor-tools").display
            )
            await pilot.press("alt+a")
            await pilot.pause()
            assert app.editor.region.width == 80 and app.sidebar_visible
            assert app.editor.content_region.height == 22
            assert 0 < app.query_one("#ai-panel").region.x < 80
            await pilot.click("#pin-ai")
            await pilot.pause()
            assert app.editor.region.width < 80
            assert app.query_one("#ai-panel").region.x == app.editor.region.right
            await pilot.click("#hide-ai")
            await pilot.pause()
            assert app.editor.region.width == 80
            await pilot.click("#main-menu")
            await pilot.pause()
            assert isinstance(app.screen, ChoiceDialog)
            await pilot.click("#choice-files")
            await pilot.pause()
            assert isinstance(app.screen, ChoiceDialog)
            await pilot.click("#choice-new")
            await pilot.pause()
            assert len(app.documents) == 2 and app.editor.region.height == 22
            await pilot.click("#main-menu")
            await pilot.pause()
            await pilot.click(app.editor, offset=(65, 20))
            await pilot.pause()
            assert len(app.screen_stack) == 1

    asyncio.run(journey())
