"""Ordered routes through the actual SDK; no changes to host routing or firewall."""

import json
import socket
import pytest
import httpx
from aivim.endpoint_transport import OrderedEndpointTransport
from aivim.settings import Settings
from aivim.ai_service import AIService, AIError
from aivim.ai_jobs import AIJob
from aivim.proposals import parse_proposal
from provider_stub import ProviderStub


def closed_endpoint():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return "http://127.0.0.1:" + str(sock.getsockname()[1]) + "/v1"


def olares(settings, urls):
    settings.ai.default_model = "olares"
    settings.ai.olares_base_urls = urls
    settings.ai.retry_on_error = False
    settings.ai.olares_connect_timeout = 0.2
    return AIService(settings=settings)


def test_lan_preferred_for_every_request_and_no_cloud_key(settings, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "DO_NOT_FORWARD")
    with ProviderStub() as lan, ProviderStub() as tail:
        s = olares(settings, [lan.url + "/v1", tail.url + "/v1"])
        assert s.request("query", instruction="probe").text == "plain response"
        assert s.request("query", instruction="probe").text == "plain response"
        assert len(lan.calls) == 2 and not tail.calls
        client = s._client("olares")
        assert client.api_key == "local-olares" and s.current_model == "olares"
        assert client._client._transport.last_endpoint == lan.url + "/v1"


def test_connection_failure_falls_back_for_stream_and_plain(settings):
    with ProviderStub() as tail:
        s = olares(settings, [closed_endpoint(), tail.url + "/v1"])
        assert s.request("query", instruction="probe").provider == "olares"
        tail.text = json.dumps({"code": "print(2)", "explanation": "new"})
        chunks = []
        result = s.request("generate", instruction="print two", on_delta=chunks.append)
        assert "".join(chunks) == tail.text
        assert s._client("olares")._client._transport.last_endpoint == tail.url + "/v1"
        assert len(tail.calls) == 2


def test_server_error_and_partial_stream_are_not_replayed(settings):
    with ProviderStub() as lan, ProviderStub() as tail:
        s = olares(settings, [lan.url + "/v1", tail.url + "/v1"])
        lan.status = 429
        with pytest.raises(AIError) as exc:
            s.request("query", instruction="probe")
        assert exc.value.code == "RATE_LIMITED" and not tail.calls
        lan.status = 200
        lan.finish = "length"
        lan.text = "partial"
        with pytest.raises(AIError) as exc:
            s.request("query", instruction="probe", on_delta=lambda _: None)
        assert exc.value.code == "INVALID_RESPONSE" and not tail.calls


def test_connection_timeout_path_and_host_header():
    attempts = []

    def handle(request):
        attempts.append(request)
        if request.url.host == "lan.invalid":
            raise httpx.ConnectTimeout("synthetic", request=request)
        return httpx.Response(200, json={"ok": True}, request=request)

    transport = OrderedEndpointTransport(
        ["http://lan.invalid:8085/v1", "http://tail.invalid:8085/api/v1"],
        0.3,
        transport=httpx.MockTransport(handle),
    )
    with httpx.Client(transport=transport) as client:
        result = client.post(
            "http://lan.invalid:8085/v1/chat/completions", json={"model": "fixture"}
        )
    assert result.status_code == 200
    assert [r.url.path for r in attempts] == ["/v1/chat/completions", "/api/v1/chat/completions"]
    assert attempts[1].headers["host"] == "tail.invalid:8085"
    assert attempts[0].extensions["timeout"]["connect"] == 0.3


@pytest.mark.parametrize(
    "urls",
    [
        ["ftp://server/v1"],
        ["http://user:password@server/v1"],
        ["http://server/v1?token=secret"],
        ["http://server/v1#fragment"],
        [1],
        ["http://server\x00/v1"],
        ["http://server:bad/v1"],
    ],
)
def test_invalid_endpoint_configuration(urls):
    with pytest.raises(ValueError):
        Settings.validate_config({"schema_version": 1, "ai": {"olares_base_urls": urls}})


def test_olares_configuration_roundtrip_and_cli(tmp_path):
    path = tmp_path / "settings.json"
    config = {
        "schema_version": 1,
        "ai": {
            "default_model": "olares",
            "olares_model": "fixture",
            "olares_base_urls": ["http://127.0.0.1:8085/v1", "http://127.0.0.2:8085/v1"],
            "olares_connect_timeout": 1,
        },
    }
    path.write_text(json.dumps(config))
    s = Settings(str(path))
    assert s.ai.default_model == "olares" and s.ai.olares_model == "fixture"
    assert s.ai.olares_base_urls == config["ai"]["olares_base_urls"]
    assert AIService(settings=s).is_model_configured("olares")
