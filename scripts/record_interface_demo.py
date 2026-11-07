"""Capture actual 2.1 controls and a real local-model full-screen response."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import tempfile
import time
os.environ.pop('NO_COLOR', None)
from aivim import __version__
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from aivim.interface_widgets import MatrixLoading
from textual.widgets import TextArea
from textual.widgets.text_area import Selection
from record_live_demo import render


async def capture(settings, base):
    project=base/'project';project.mkdir()
    script=project/'morning.sh';script.write_text('#!/usr/bin/env bash\n\necho "Good morning"\ndu -sh .\n')
    guide=project/'guide.md';guide.write_text('Keep scripts short and readable.\n')
    app=TerminalWorkspace(filename=str(script),settings=settings,project=project)
    app.session_store.path=base/'capture-session.json'
    app.user_preferences.store.path=base/'capture-preferences.json'
    app.recent_files=[];app.title=f'AIVim {__version__} · a little more effortless'
    frames=[]
    def snap(name,duration=1200):
        path=base/f'{len(frames):03d}-{name}.svg';path.write_text(app.export_screenshot());frames.append((path,duration))
    async with app.run_test(size=(110,36)) as pilot:
        app.editor.cursor_blink=False
        await app.open_document(str(guide));await app.remove_document(app.current_id)
        await app.new_document('helpers.py','def greet(name):\n    return f"Hello, {name}"\n')
        await pilot.pause()
        app.switch_document(next(d.id for d in app.documents.values() if d.name=='morning.sh'))
        await pilot.click('#live-mode');await pilot.pause();snap('live-review')
        await pilot.click('#live-mode');await pilot.pause();snap('live-auto')
        await pilot.click('#live-mode');await pilot.pause()
        app.action_project_generate();await pilot.pause()
        await pilot.press(*'Use @gui');await pilot.pause();snap('file-mentions',2000)
        await pilot.press('tab','enter',*'Keep this script readable.','enter',*'Explain changes before applying.')
        await pilot.pause();snap('multiline-prompt',1600)
        app.screen.dismiss(None);await pilot.pause()
        app.action_settings();await pilot.pause();snap('settings',1800)
        app.screen.dismiss(None);await pilot.pause()
        app.push_screen(MatrixLoading());await pilot.pause(.08);snap('matrix-startup',1200)
        await pilot.pause(.7)
        app.editor.selection=Selection((0,0),app.editor.document.end)
        app.query_one('#instruction',TextArea).load_text('Explain this Bash script in 24 short numbered lines, including helpful practical context. Do not execute it.')
        app.submit_action('query');await pilot.pause();app.action_fullscreen_ai();await pilot.pause();snap('ai-thinking',400)
        deadline=time.monotonic()+settings.ai.timeout+5;last_capture=0
        while time.monotonic()<deadline and app.active:
            await pilot.pause(.08)
            if time.monotonic()-last_capture>.5:
                snap('streaming-response',130);last_capture=time.monotonic()
        if app.active or not app.records or app.records[0].state!='Answered':raise RuntimeError('Actual-model response failed.')
        app.query_one('#result',TextArea).scroll_home(animate=False)
        await pilot.pause();snap('fullscreen-response',2200)
        assert app.query_one('#ai-panel').region.y>=1
        report={'release':__version__,'provider':app.service.current_model,'model':app.service.models()[app.service.current_model],
                'commands_executed':False,'idle_inference_waits_shortened':True,
                'captures':['live-mode rotation','open/recent file mentions','five-line prompt','settings','matrix startup','full-screen real response']}
    return frames,report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='docs/assets/interface-2.1.gif');args=parser.parse_args()
    settings=Settings();settings.ai.max_tokens=min(settings.ai.max_tokens,2048)
    with tempfile.TemporaryDirectory() as directory:
        frames,report=asyncio.run(capture(settings,Path(directory)))
        asyncio.run(render(frames,Path(args.output),report))
if __name__=='__main__':main()
