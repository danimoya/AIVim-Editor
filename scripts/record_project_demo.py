"""Capture an actual Olares project proposal and explicit multi-file acceptance."""
import asyncio
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import time
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from aivim.project_widgets import ChangeReview
from record_live_demo import render

async def capture(settings,root,frames_dir):
    path=root/'greet.py';path.write_text('def greet(name):\n    return f"Hello, {name}!"\n')
    (root/'README.md').write_text('# Greeting\n\nCall greet with a name.\n')
    app=TerminalWorkspace(filename=str(path),settings=settings,project=root)
    app.session_store.path=frames_dir/"capture-session.json"
    app.title='AIVim 2.0 · one thought, several files'
    frames=[];previous=None
    def snap(duration=120):
        nonlocal previous
        svg=app.export_screenshot();key=hashlib.sha256(svg.encode()).hexdigest()
        if key==previous:return
        previous=key;p=frames_dir/f'{len(frames):04d}.svg';p.write_text(svg);frames.append((p,duration))
    async with app.run_test(size=(110,36)) as pilot:
        app.editor.cursor_blink=False
        app.source_file(str(path));app.source_file(str(root/'README.md'))
        app.action_project_generate();await pilot.pause();snap(700)
        instruction='Update both greet.py and README.md: greet defaults to World, has a short docstring, and the README shows greet() and greet("Ada") examples.'
        for start in range(0,len(instruction),4):
            await pilot.press(*instruction[start:start+4]);snap(60)
        snap(450);await pilot.press('enter')
        deadline=time.monotonic()+settings.ai.timeout+10
        while time.monotonic()<deadline:
            await pilot.pause(.05);snap(90)
            if isinstance(app.screen,ChangeReview):break
            if not app.project_busy:raise RuntimeError(str(app.query_one('#status').render()))
        if not isinstance(app.screen,ChangeReview):raise RuntimeError('Project proposal timed out')
        await pilot.pause();snap(1800)
        plan=app.screen.changeset
        assert {c.path for c in plan.changes}=={'greet.py','README.md'}
        assert 'World' not in path.read_text()
        await pilot.click('#changes-apply');await pilot.pause();snap(1800)
        ast.parse(path.read_text());assert 'World' in path.read_text()
        assert app.last_checkpoint
        report={'model':app.service.models()[app.service.current_model],'provider':app.service.current_model,
                'files':[c.path for c in plan.changes],'review_required':True,'commands_executed':False,
                'idle_inference_waits_shortened':True,'release':'2.0.0'}
    return frames,report

with tempfile.TemporaryDirectory() as directory:
    base=Path(directory);root=base/'project';root.mkdir();frames_dir=base/'frames';frames_dir.mkdir()
    settings=Settings();settings.ai.max_tokens=min(settings.ai.max_tokens,2048)
    frames,report=asyncio.run(capture(settings,root,frames_dir))
    asyncio.run(render(frames,Path('docs/assets/project-2.0.gif'),report))
