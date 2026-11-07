import asyncio
from pathlib import Path
import sys
import time
from aivim.language_server import LanguageClient,utf16_position,character_location
from aivim.tui import TerminalWorkspace
from aivim.project_widgets import ChangeReview
from test_tui_workspace import settle


def test_utf16_positions_with_emoji():
    text='😀 name\nsecond'
    assert utf16_position(text,(0,2))=={'line':0,'character':3}
    assert character_location(text,{'line':0,'character':3})==(0,2)


def test_real_stdio_protocol_sync_completion_definition_and_rename(tmp_path):
    command=[sys.executable,str(Path(__file__).with_name('lsp_stub.py'))]
    client=LanguageClient(command,tmp_path)
    try:
        path=tmp_path/'sample.py';path.write_text('old=1\n')
        uri=client.open_document(path,'old=1\n','python')
        position={'textDocument':{'uri':uri},'position':{'line':0,'character':1}}
        assert client.request('textDocument/completion',position)[0]['label']=='print'
        assert client.request('textDocument/definition',position)[0]['uri']==uri
        assert client.request('textDocument/rename',{**position,'newName':'new'})['changes'][uri][0]['newText']=='new'
        client.change_document(uri,'old=2\n',2)
        assert client.notifications.get(timeout=2)['method']=='textDocument/publishDiagnostics'
    finally:client.close()
    assert client.process.poll() is not None


def test_language_tools_review_rename_in_terminal(settings,tmp_path):
    async def journey():
        path=tmp_path/'sample.py';path.write_text('old=1\n')
        app=TerminalWorkspace(filename=str(path),settings=settings,project=tmp_path)
        async with app.run_test(size=(110,40)) as pilot:
            client=LanguageClient([sys.executable,str(Path(__file__).with_name('lsp_stub.py'))],tmp_path)
            app.language_started(client)
            app.action_rename_symbol();await pilot.pause();app.screen.dismiss('new')
            await settle(pilot,lambda:isinstance(app.screen,ChangeReview))
            assert path.read_text()=='old=1\n'
            await pilot.pause();await pilot.click('#changes-apply');await pilot.pause()
            assert path.read_text()=='new=1\n'
    asyncio.run(journey())
