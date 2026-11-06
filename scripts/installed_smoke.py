"""Run with a clean wheel environment, from outside the source directory."""
import importlib.metadata
import importlib.resources
import subprocess
import sys
from aivim import __version__
import aivim
from pathlib import Path
assert Path(aivim.__file__).resolve().is_relative_to(Path(sys.prefix).resolve()), "Imports must come from the installed wheel environment"
from aivim.web import create_app
from aivim.settings import Settings
from aivim.ai_service import AIService
from aivim.editor import Editor
from aivim.tui import TerminalWorkspace

assert importlib.metadata.version('aivim')==__version__
assert importlib.resources.files('aivim').joinpath('py.typed').is_file()
assert importlib.resources.files('aivim').joinpath('tui.tcss').is_file()
for resource in ['templates/index.html','static/app.js','static/app.css']:
    assert importlib.resources.files('aivim.web').joinpath(resource).is_file()
for module in ['aivim.run_editor','aivim.model_download','aivim.config_migrate']:
    subprocess.run([sys.executable,'-m',module,'--help'],check=True,stdout=subprocess.DEVNULL)
settings=Settings('/nonexistent/synthetic-settings.json')
editor=Editor(settings=settings,ai_service=AIService(settings=settings))
for key in ['i','A','é','界',27]:editor.handle_input(key)
assert editor.buffer.get_content()=='Aé界';editor.handle_input('u');assert editor.buffer.get_content()==''
app=create_app(AIService(settings=settings));client=app.test_client()
assert client.get('/').status_code==200 and client.get('/static/app.js').status_code==200
assert client.get('/health').json['status']=='ok'
assert not any(name in sys.modules for name in ['llama_cpp'])
print('Installed wheel: entrypoints, versions, real dispatch, health and packaged assets passed; no native engine loaded')

import asyncio
async def terminal_smoke():
    workspace=TerminalWorkspace(settings=settings)
    async with workspace.run_test(size=(110,40)) as pilot:
        await pilot.press('i','A','é','界','escape')
        assert workspace.editor.text=='Aé界'
        await pilot.press('f2')
        assert len(workspace.screen_stack)==2
        await pilot.press('escape')
asyncio.run(terminal_smoke())
print('Installed terminal workspace: editing and context menu passed')
