"""HTTPS OpenAI-compatible connections and explicit private credential storage."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import ssl
from urllib.parse import urlsplit, urlunsplit
import uuid

import httpx

from .file_store import FileStore


@dataclass
class Connection:
    base_url: str
    model: str
    token: str = ""
    ca_file: str = ""
    remember: bool = False


def normalize_url(value):
    value = value.strip().rstrip("/")
    if not value or len(value) > 2048 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError("Enter a valid HTTPS API URL.")
    parsed = urlsplit(value)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Use an API URL without credentials, query parameters or fragments.")
    parsed.port
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    ):
        raise ValueError(
            "Use HTTPS for remote models. HTTP is supported only on loopback for development."
        )
    path = parsed.path.rstrip("/")
    for suffix in ("/chat/completions", "/models"):
        if path.endswith(suffix):
            path = path[: -len(suffix)]
            break
    return urlunsplit((parsed.scheme, parsed.netloc, path or "/v1", "", ""))


def ssl_context(ca_file=""):
    context = ssl.create_default_context()
    if ca_file:
        context.load_verify_locations(cafile=str(Path(ca_file).expanduser()))
    return context


def stored_token(path):
    if not path:
        return ""
    target = Path(path).expanduser()
    if target.is_symlink():
        raise ValueError("Token file must not be a symlink.")
    info = target.stat()
    if info.st_size > 16384 or (
        os.name != "nt" and (info.st_mode & 0o077 or info.st_uid != os.getuid())
    ):
        raise ValueError("Token file must be private to the current user (mode 600).")
    return target.read_text(encoding="utf-8").strip()


def token_for(settings, credentials=None):
    if credentials and credentials.get("compatible"):
        return credentials["compatible"]
    return os.environ.get(settings.ai.compatible_token_env, "") or stored_token(
        settings.ai.compatible_token_file
    )


def discover_models(base_url, token="", ca_file=""):
    url = normalize_url(base_url)
    headers = {"Authorization": "Bearer " + token} if token else {}
    with httpx.Client(
        verify=ssl_context(ca_file),
        trust_env=False,
        follow_redirects=False,
        timeout=httpx.Timeout(10, connect=3),
        headers=headers,
    ) as client:
        response = client.get(url + "/models")
        if response.status_code in (401, 403):
            raise ValueError("Access denied. Check the bearer token and model permissions.")
        if response.status_code == 404:
            raise ValueError("Models API not found. Check the base URL (usually /v1).")
        if response.status_code != 200:
            raise ValueError("Model discovery failed: HTTP " + str(response.status_code))
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ValueError("Expected an OpenAI-compatible /models response.")
        models = [
            row["id"]
            for row in data["data"]
            if isinstance(row, dict) and isinstance(row.get("id"), str) and row["id"]
        ]
        if not models:
            raise ValueError("The server returned no model IDs; you can enter one manually.")
        return models[:200]


def save_connection(settings, connection):
    """Merge public settings atomically; put remembered tokens in a separate private file."""
    from .settings import Settings

    base_url = normalize_url(connection.base_url)
    model = connection.model.strip()
    if not model or len(model) > 256 or any(ord(c) < 32 for c in model):
        raise ValueError("Enter the served model ID or discover it from the server.")
    if any(c in connection.token for c in "\r\n\0") or len(connection.token) > 16384:
        raise ValueError("Enter a bearer token without newlines.")
    if connection.ca_file:
        ssl_context(connection.ca_file)
    path = settings.config_path
    store = FileStore()
    loaded = store.load(path)
    if not loaded:
        raise ValueError(loaded.message)
    if loaded.content.lstrip().startswith("["):
        raise ValueError("Use a JSON settings file; migrate legacy INI before saving connections.")
    data = json.loads(loaded.content) if loaded.content.strip() else {"schema_version": 1}
    token_path = settings.ai.compatible_token_file if connection.remember else ""
    created = None
    try:
        if connection.remember and connection.token:
            from .private_files import restrict

            directory = Path("~/.local/state/aivim/keys").expanduser()
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if directory.is_symlink():
                raise ValueError("Credential directory must not be a symlink.")
            restrict(directory, directory=True)
            created = directory / (uuid.uuid4().hex + ".token")
            fd = os.open(created, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as handle:
                restrict(created)
                handle.write(connection.token)
                handle.flush()
                os.fsync(handle.fileno())
            token_path = str(created)
        values = {
            "default_model": "compatible",
            "compatible_base_url": base_url,
            "compatible_model": model,
            "compatible_ca_file": connection.ca_file,
            "compatible_token_file": token_path,
        }
        data.setdefault("ai", {}).update(values)
        Settings.validate_config(data)
        saved = store.save(path, json.dumps(data, indent=2) + "\n", loaded.identity)
        if not saved:
            raise ValueError(saved.message)
        for key, value in values.items():
            setattr(settings.ai, key, value)
        return connection.token
    except Exception:
        if created:
            created.unlink(missing_ok=True)
        raise
