"""OpenShift-style HTTPS discovery and generation with real certificate validation."""

import asyncio
import json
import os
import ssl
import time

import httpx
import pytest
import trustme
from textual.widgets import Input, Checkbox, TextArea, Select, Static

from aivim.compatible import (
    Connection,
    discover_models,
    normalize_url,
    save_connection,
    stored_token,
)
from aivim.ai_service import AIService, AIError
from aivim.settings import Settings
from aivim.tui import TerminalWorkspace
from aivim.tui_widgets import ConnectionDialog
from provider_stub import ProviderStub
from test_tui_workspace import settle


@pytest.fixture
def tls_server(tmp_path):
    ca = trustme.CA()
    cert = ca.issue_cert("127.0.0.1", "localhost")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert.configure_cert(context)
    ca_file = tmp_path / "cluster-ca.pem"
    ca.cert_pem.write_to_path(ca_file)
    with ProviderStub(ssl_context=context) as stub:
        stub.models = ["openshift-coder"]
        stub.required_token = "synthetic-cluster-token"
        yield stub, str(ca_file)


def test_https_ca_auth_discovery_and_real_stream(settings, tls_server, monkeypatch):
    stub, ca_file = tls_server
    url = stub.url + "/v1"
    assert discover_models(url, stub.required_token, ca_file) == ["openshift-coder"]
    with pytest.raises(httpx.ConnectError):
        discover_models(url, stub.required_token)
    with pytest.raises(ValueError, match="Access denied"):
        discover_models(url, "wrong-token", ca_file)
    settings.ai.default_model = "compatible"
    settings.ai.compatible_base_url = url
    settings.ai.compatible_model = stub.models[0]
    settings.ai.compatible_ca_file = ca_file
    settings.ai.retry_on_error = False
    monkeypatch.setenv("OPENAI_API_KEY", "CLOUD_KEY_MUST_NOT_BE_USED")
    monkeypatch.setenv("AIVIM_COMPATIBLE_API_KEY", stub.required_token)
    service = AIService(settings=settings)
    stub.text = json.dumps({"code": "print(2)", "explanation": "ok"})
    chunks = []
    result = service.request("generate", instruction="print two", on_delta=chunks.append)
    assert result.provider == "compatible" and result.model == "openshift-coder"
    assert (
        "".join(chunks) == stub.text
        and service._client("compatible").api_key == stub.required_token
    )


def test_token_saved_separately_and_existing_provider_preserved(settings, tls_server):
    stub, ca_file = tls_server
    original = {
        "schema_version": 1,
        "editor": {"tabstop": 8},
        "ai": {
            "default_model": "olares",
            "olares_model": "keep-this-model",
            "olares_base_urls": ["http://127.0.0.1:8085/v1"],
        },
    }
    settings.config_path.parent.mkdir(parents=True, exist_ok=True)
    settings.config_path.write_text(json.dumps(original))
    save_connection(
        settings, Connection(stub.url, stub.models[0], stub.required_token, ca_file, True)
    )
    saved = settings.config_path.read_text()
    assert stub.required_token not in saved
    data = json.loads(saved)
    assert data["ai"]["olares_model"] == "keep-this-model" and data["editor"]["tabstop"] == 8
    restored = Settings(str(settings.config_path))
    assert stored_token(restored.ai.compatible_token_file) == stub.required_token
    if os.name != "nt":
        assert os.stat(restored.ai.compatible_token_file).st_mode & 0o777 == 0o600
    assert restored.ai.default_model == "compatible" and restored.ai.compatible_base_url.endswith(
        "/v1"
    )


def test_session_token_is_not_persisted(settings, tls_server):
    stub, ca_file = tls_server
    token = save_connection(
        settings, Connection(stub.url, stub.models[0], stub.required_token, ca_file, False)
    )
    assert token == stub.required_token
    assert stub.required_token not in settings.config_path.read_text()
    assert not settings.ai.compatible_token_file


@pytest.mark.parametrize(
    "url",
    [
        "http://external.example/v1",
        "https://user:secret@example/v1",
        "https://example/v1?token=secret",
        "https://example/v1#fragment",
        "https://bad\x00.example/v1",
    ],
)
def test_remote_endpoint_validation(url):
    with pytest.raises(ValueError):
        normalize_url(url)


def test_pasted_route_and_completion_urls():
    assert normalize_url("https://coder.apps.example.com") == "https://coder.apps.example.com/v1"
    assert (
        normalize_url("https://coder.apps.example.com/v1/chat/completions")
        == "https://coder.apps.example.com/v1"
    )
    assert (
        normalize_url("https://coder.apps.example.com/api/v1/models")
        == "https://coder.apps.example.com/api/v1"
    )


def test_connection_dialog_discover_save_and_generate(settings, tls_server):
    stub, ca_file = tls_server

    async def journey():
        app = TerminalWorkspace(settings=settings, connect_on_start=True)
        async with app.run_test(size=(110, 44)) as pilot:
            await pilot.pause()
            assert isinstance(app.screen, ConnectionDialog)
            dialog = app.screen
            dialog.query_one("#connect-url", Input).value = stub.url
            dialog.query_one("#connect-token", Input).value = stub.required_token
            assert dialog.query_one("#connect-token", Input).password
            dialog.query_one("#connect-ca", Input).value = ca_file
            dialog.query_one("#connect-remember", Checkbox).value = True
            await pilot.click("#connect-discover")
            await settle(
                pilot, lambda: dialog.query_one("#connect-model", Input).value == "openshift-coder"
            )
            await pilot.click("#connect-save")
            await pilot.pause()
            assert app.query_one("#provider", Select).value == "compatible"
            assert app.service.models()["compatible"] == "openshift-coder"
            app.query_one("#instruction", TextArea).load_text("print two")
            app.query_one("#ai-action", Select).value = "generate"
            stub.text = json.dumps({"code": "print(2)", "explanation": "HTTPS generation"})
            app.action_submit()
            await settle(pilot, lambda: app.proposal is not None)
            app.action_accept()
            await pilot.pause()
            assert app.editor.text == "print(2)"

    asyncio.run(journey())
