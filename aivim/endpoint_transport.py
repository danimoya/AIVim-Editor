"""Prefer LAN on every request; fail over only before a connection is established."""

from __future__ import annotations

import logging
import httpx


class OrderedEndpointTransport(httpx.BaseTransport):
    def __init__(self, endpoints, connect_timeout=2.0, *, transport=None):
        self.endpoints = tuple(httpx.URL(url.rstrip("/") + "/") for url in endpoints)
        if not self.endpoints:
            raise ValueError("At least one endpoint is required")
        self.connect_timeout = connect_timeout
        self.transport = transport or httpx.HTTPTransport(
            retries=0,
            trust_env=False,
            limits=httpx.Limits(max_connections=2, max_keepalive_connections=0),
        )
        self.last_endpoint = None

    def handle_request(self, request):
        primary = self.endpoints[0]
        prefix = primary.raw_path.rstrip(b"/")
        if not request.url.raw_path.startswith(prefix + b"/"):
            raise httpx.UnsupportedProtocol("Request is outside the configured API path")
        suffix = request.url.raw_path[len(prefix) :]
        content = request.read()
        for index, endpoint in enumerate(self.endpoints):
            target = endpoint.copy_with(raw_path=endpoint.raw_path.rstrip(b"/") + suffix)
            headers = request.headers.copy()
            headers.pop("host", None)
            extensions = dict(request.extensions)
            timeout = dict(extensions.get("timeout", {}))
            current = timeout.get("connect")
            timeout["connect"] = (
                min(current, self.connect_timeout) if current is not None else self.connect_timeout
            )
            extensions["timeout"] = timeout
            attempt = httpx.Request(
                request.method, target, headers=headers, content=content, extensions=extensions
            )
            try:
                response = self.transport.handle_request(attempt)
                self.last_endpoint = str(endpoint).rstrip("/")
                return response
            except (httpx.ConnectError, httpx.ConnectTimeout):
                if index + 1 == len(self.endpoints):
                    raise
                logging.info("Olares route %s unavailable; trying next configured route", index + 1)
        raise AssertionError("Unreachable endpoint loop")

    def close(self):
        self.transport.close()
