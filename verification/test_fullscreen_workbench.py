"""Full-screen interactions use the same controls, request and response widgets."""
import asyncio
import json

import pytest
from textual.widgets import Button, Select, TextArea
from textual.widgets.text_area import Selection

from aivim.tui import TerminalWorkspace
from aivim.tui_widgets import TextDialog
from provider_stub import ProviderStub
from test_ai_jobs import service
from test_tui_workspace import settle


@pytest.mark.parametrize('size', [(60, 16), (80, 24), (120, 40)])
def test_fullscreen_controls_collapse_restore_and_preserve_state(settings, size):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=size) as pilot:
            app.editor.load_text('selected code')
            selection = Selection((0, 0), (0, 8))
            app.editor.selection = selection
            await pilot.press('alt+a')
            await pilot.pause()
            prompt = app.query_one('#instruction', TextArea)
            prompt.load_text('Keep this prompt\nand its second line')
            result = app.query_one('#result', TextArea)
            result.load_text('\n'.join('Response ' + str(i) for i in range(100)))
            await pilot.click('#fullscreen-ai')
            await pilot.pause()
            controls = app.query_one('#ai-controls')
            assert controls.display and controls.region.right <= result.region.x
            assert result.region.right <= size[0] and result.read_only
            assert result.region.height >= size[1] - 6
            result.scroll_to(y=20, animate=False)
            await pilot.pause()
            reading = result.scroll_y
            width = result.region.width
            await pilot.click('#toggle-ai-controls')
            await settle(pilot, lambda: not controls.display)
            assert result.region.width > width and result.region.width >= size[0] - 4
            assert result.scroll_y == reading
            app.update_ai_response(result.text + '\nMore streamed text')
            await pilot.pause()
            assert result.scroll_y == reading
            await pilot.press('alt+b')
            await settle(pilot, lambda: controls.display and app.focused is prompt)
            assert prompt.text == 'Keep this prompt\nand its second line'
            assert app.editor.selection == selection
            await pilot.press('escape')
            await pilot.pause()
            assert not app.ai_fullscreen and controls.display
            assert not app.query_one('#toggle-ai-controls').display
            assert app.editor.region.width == size[0]
    asyncio.run(journey())


def test_fullscreen_stream_accept_and_next_request_cancel_without_leaving(settings):
    async def journey(stub):
        stub.text = json.dumps({'code': 'echo hello\n', 'explanation': 'A greeting'})
        stub.stream_gate.clear()
        app = TerminalWorkspace(settings=settings, service=service(settings, stub))
        async with app.run_test(size=(100, 32)) as pilot:
            app.add_source('Guide', 'Use a friendly greeting')
            await pilot.press('alt+a')
            await pilot.click('#fullscreen-ai')
            app.query_one('#ai-action', Select).value = 'generate'
            prompt = app.query_one('#instruction', TextArea)
            prompt.load_text('Print hello in Bash')
            await pilot.click('#submit')
            await settle(pilot, lambda: app.active is not None)
            assert app.ai_fullscreen
            await pilot.click('#toggle-ai-controls')
            await settle(pilot, lambda: app.query_one('#cancel-result').display)
            stub.stream_gate.set()
            await settle(pilot, lambda: app.proposal is not None)
            assert app.ai_fullscreen and app.ai_controls_collapsed
            assert app.query_one('#accept', Button).display
            await pilot.click('#accept')
            await settle(pilot, lambda: app.editor.text == 'echo hello\n')
            assert app.ai_fullscreen and app.ai_controls_collapsed
            sent = json.loads(stub.calls[0][1]['messages'][-1]['content'])
            assert 'Use a friendly greeting' in sent['context']
            await pilot.press('f5')
            await settle(pilot, lambda: not app.ai_controls_collapsed and app.focused is prompt)
            assert app.ai_fullscreen
            stub.stream_gate.clear()
            prompt.load_text('Print goodbye in Bash')
            await pilot.press('ctrl+enter')
            await settle(pilot, lambda: app.active is not None)
            await pilot.click('#toggle-ai-controls')
            await settle(pilot, lambda: app.query_one('#cancel-result').display)
            await pilot.click('#cancel-result')
            await settle(pilot, lambda: app.active is None)
            assert app.ai_fullscreen and app.editor.text == 'echo hello\n'
            assert app.records[0].state == 'Cancelled'
            stub.stream_gate.set()
    with ProviderStub() as stub:
        asyncio.run(journey(stub))


def test_fullscreen_action_dropdown_and_context_controls_are_reachable(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test(size=(80, 24)) as pilot:
            app.add_source('Reference', 'Explicit source content')
            await pilot.press('alt+a')
            await pilot.click('#fullscreen-ai')
            selector = app.query_one('#ai-action', Select)
            await pilot.click(selector)
            await pilot.pause()
            overlay = selector.query_one('SelectOverlay')
            region = overlay.content_region
            assert region.height >= 5
            for row in range(5):
                assert app.get_widget_at(region.x + 3, region.y + row)[0] is overlay
            await pilot.click(overlay, offset=(3, 5))
            assert selector.value == 'query'
            app.query_one('#ai-details').collapsed = False
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            button = app.query_one('#context', Button)
            button.scroll_visible(animate=False)
            await pilot.wait_for_scheduled_animations()
            region = button.region
            assert app.get_widget_at(region.x + 2, region.y)[0] is button
            assert await pilot.click(button, offset=(2, 0))
            await settle(pilot, lambda: isinstance(app.screen, TextDialog))
            assert 'Explicit source content' in app.screen.query_one('#dialog-text', TextArea).text
            await pilot.press('escape')
            assert app.ai_fullscreen
    asyncio.run(journey())
