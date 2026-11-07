"""Exercise 100 real SDK live replacements against a deterministic loopback model."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'verification'))
from provider_stub import ProviderStub
from test_ai_jobs import service
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from textual.widgets import Checkbox

async def stress(settings, stub):
    app = TerminalWorkspace(settings=settings, service=service(settings, stub))
    app.session_store.path=Path(settings.config_path).parent/"stress-session.json"
    async with app.run_test(size=(100,28)) as pilot:
        await pilot.press('f4')
        app.query_one('#live', Checkbox).value = True
        app.query_one('#auto', Checkbox).value = True
        app.writing_effect = False
        await pilot.pause()
        for n in range(100):
            # Exercise the real Enter boundary, SDK stream, queue and undo engine.
            app.editor.insert(f'Print block {n}')
            await pilot.press('enter', 'enter')
            while app.active or app.pending or app.proposal:
                await pilot.pause(.02)
            assert app.records[0].state == 'Accepted', app.records[0].result
            assert f'Print block {n}' not in app.editor.text
            if n % 10 == 0:
                app.editor.undo(); await pilot.pause()
                assert f'Print block {n}' in app.editor.text
                app.editor.redo(); await pilot.pause()
                assert f'Print block {n}' not in app.editor.text
        assert app.editor.text.count('print(2)') == 100
        print(json.dumps({'blocks':100,'accepted':len(stub.calls),'undo_redo_checks':10,'misplaced_replacements':0}))

with tempfile.TemporaryDirectory() as d, ProviderStub() as stub:
    settings=Settings(str(Path(d)/'settings.json'));settings.file.auto_backup=False
    stub.text=json.dumps({'code':'print(2)','explanation':'Generated'})
    asyncio.run(stress(settings,stub))
