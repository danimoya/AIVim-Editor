"""Exercise rendered action menus, including mouse hit targets above the panel."""
import asyncio

import pytest
from textual.widgets import Button, Select
from textual.widgets.text_area import Selection

from aivim.tui import TerminalWorkspace
from aivim.tui_widgets import ChoiceDialog
from test_tui_workspace import settle


ACTIONS = ["improve", "generate", "explain", "analyze", "query"]


@pytest.mark.parametrize("size", [(80, 24), (132, 46)])
@pytest.mark.parametrize("pinned", [False, True])
def test_workbench_dropdown_exposes_every_action(settings, size, pinned):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=size) as pilot:
            await pilot.press("alt+a")
            if pinned:
                app.action_pin_ai()
            await pilot.pause()
            editor_region = app.editor.region
            selector = app.query_one("#ai-action", Select)
            for index, action in enumerate(ACTIONS):
                await pilot.click(selector)
                await pilot.pause()
                overlay = selector.query_one("SelectOverlay")
                assert selector.expanded and overlay.option_count == len(ACTIONS)
                region = overlay.content_region
                assert region.height >= len(ACTIONS)
                # The DOM can contain all options while later siblings paint over
                # them. Assert the actual rendered mouse target of every row.
                for row in range(len(ACTIONS)):
                    assert app.get_widget_at(region.x + 3, region.y + row)[0] is overlay
                await pilot.click(overlay, offset=(3, index + 1))
                await pilot.pause()
                assert selector.value == action and not selector.expanded
                assert app.editor.region == editor_region
            selector.focus()
            await pilot.press("enter", "home", "down", "enter")
            assert selector.value == "generate" and not selector.expanded
            if not pinned:
                assert app.editor.region.width == size[0]

    asyncio.run(journey())


@pytest.mark.parametrize("size", [(80, 24), (60, 16)])
def test_workspace_ai_actions_menu_exposes_and_routes_every_action(settings, size):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        submitted = []
        app.submit_action = submitted.append
        async with app.run_test(size=size) as pilot:
            app.editor.load_text("selected code")
            selection = Selection((0, 0), (0, 8))
            app.editor.selection = selection
            for action in ACTIONS:
                assert await pilot.click("#main-menu", offset=(2, 0))
                await settle(pilot, lambda: bool(app.screen.query("#choice-ai")))
                assert await pilot.click("#choice-ai", offset=(2, 0))
                await settle(pilot, lambda: bool(app.screen.query("#choice-query")))
                assert isinstance(app.screen, ChoiceDialog)
                for button in app.screen.query(Button):
                    region = button.region
                    assert app.get_widget_at(region.x + 2, region.y)[0] is button
                assert await pilot.click("#choice-" + action, offset=(2, 0))
                await pilot.pause()
                assert app.editor.selection == selection
                if action in ("explain", "analyze"):
                    assert submitted[-1] == action
                else:
                    assert app.query_one("#ai-action", Select).value == action
                    assert app.focused.id == "instruction"
                app.collapse_ai()
                await pilot.pause()

    asyncio.run(journey())
