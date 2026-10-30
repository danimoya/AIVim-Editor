"""Real dispatch, real constants; replace only external boundaries."""
import socket
import pytest
from aivim.editor import Editor
from aivim.ai_service import AIService
from aivim.settings import Settings


@pytest.fixture(autouse=True)
def isolated_boundaries(tmp_path,monkeypatch):
    monkeypatch.setenv('HOME',str(tmp_path));monkeypatch.delenv('OPENAI_API_KEY',raising=False);monkeypatch.delenv('ANTHROPIC_API_KEY',raising=False)
    original=socket.socket.connect
    def connect(sock,address):
        if isinstance(address,tuple) and address[0] not in ('127.0.0.1','localhost','::1'):raise AssertionError('External network is forbidden in tests')
        return original(sock,address)
    monkeypatch.setattr(socket.socket,'connect',connect)

@pytest.fixture
def settings(tmp_path):
    s=Settings(str(tmp_path/'settings.json'));s.file.auto_backup=False;s.editor.autoindent=False;return s

@pytest.fixture
def editor(settings):
    return Editor(settings=settings,ai_service=AIService(settings=settings,credentials={}))
