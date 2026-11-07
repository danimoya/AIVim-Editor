"""Daily-use release contracts: recovery, editing, limits and non-executing checks."""
import asyncio
import json
import os
from pathlib import Path
from textual.widgets import SelectionList
from aivim.tui import TerminalWorkspace
from aivim.tui_model import Request
from aivim.checks import syntax_check
from aivim.session import SessionStore


def test_private_atomic_recovery_and_corruption(settings):
    store = SessionStore(settings.config_path)
    store.save({'documents': [{'name': 'draft.sh', 'content': 'echo hello'}]})
    assert store.load()['documents'][0]['content'] == 'echo hello'
    if os.name != 'nt': assert store.path.stat().st_mode & 0o077 == 0
    store.path.write_text('{broken')
    assert store.load() is None


def test_workspace_restore_preserves_unsaved_sources_cursor_and_preferences(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test() as pilot:
            await pilot.press('i', 'a', 'b', 'c', 'escape')
            app.add_source('Context', 'source snapshot')
            app.add_source('Private', 'unchecked')
            app.query_one('#source-list', SelectionList).deselect(app.sources[-1].id)
            app.vim_enabled = False
            app.snapshot_session()
        restored = TerminalWorkspace(settings=settings, restore_session=True)
        async with restored.run_test() as pilot:
            assert restored.editor.text == 'abc' and restored.document.dirty
            assert not restored.vim_enabled
            assert len(restored.sources) == 2
            assert restored.sources[1].id not in restored.query_one('#source-list', SelectionList).selected
            assert not restored.active and not restored.pending
    asyncio.run(journey())


def test_search_replace_undo_goto_and_large_file_selection(settings):
    async def journey():
        app = TerminalWorkspace(settings=settings)
        async with app.run_test() as pilot:
            app.editor.load_text('first\nneedle one\nneedle two')
            await pilot.pause()
            app.find_text('needle'); assert app.editor.selected_text == 'needle'
            app.replace_all('needle', 'match')
            assert app.editor.text == 'first\nmatch one\nmatch two'
            app.editor.undo(); assert 'needle' in app.editor.text
            app.goto_line('3'); assert app.editor.cursor_location == (2, 0)
            app.editor.load_text('x'*100000 + '\nreturn 1')
            await pilot.pause()
            # A selected function from a large document fits the actual AI budget.
            app.service.credentials['openai'] = 'synthetic'
            request = app.make_request(app.document, 100001, 100009, 'improve', 'Use two')
            assert request and request.original == 'return 1'
    asyncio.run(journey())


def test_source_refresh_is_explicit(settings, tmp_path):
    async def journey():
        path = tmp_path/'style.md'; path.write_text('old')
        app = TerminalWorkspace(settings=settings)
        async with app.run_test():
            app.source_file(str(path)); path.write_text('new')
            assert app.sources[0].content == 'old'
            app.action_refresh_sources(); assert app.sources[0].content == 'new'
    asyncio.run(journey())


def test_syntax_checks_never_execute(tmp_path):
    target = tmp_path/'executed'
    assert syntax_check('import pathlib; pathlib.Path('+repr(str(target))+').touch()', 'python')[0]
    assert not target.exists()
    assert syntax_check('def broken(', 'python')[0] is False
    assert syntax_check('{"valid":true}', 'json')[0]
    assert syntax_check('{invalid}', 'json')[0] is False


def test_recovery_survives_forced_process_exit(settings):
    import subprocess
    import sys
    import time
    script = '''import asyncio,sys
from aivim.tui import TerminalWorkspace
from aivim.settings import Settings
async def main():
 app=TerminalWorkspace(settings=Settings(sys.argv[1]))
 async with app.run_test() as pilot:
  app.editor.insert("unsaved after a crash")
  await pilot.pause()
  app.snapshot_session()
  await asyncio.sleep(60)
asyncio.run(main())
'''
    proc = subprocess.Popen([sys.executable, '-c', script, str(settings.config_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    store = SessionStore(settings.config_path, unique=True)
    try:
        deadline = time.monotonic()+10
        while time.monotonic()<deadline and not store.load(): time.sleep(.05)
        assert store.load()['documents'][0]['content'] == 'unsaved after a crash'
    finally:
        proc.kill(); proc.wait(timeout=5)
    assert store.load()['documents'][0]['content'] == 'unsaved after a crash'
