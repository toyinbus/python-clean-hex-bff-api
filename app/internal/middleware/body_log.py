"""Request/response body logging (opt-in debugging aid).

Enabled only when ``LOG_BODIES=true``. Logs the request and response bodies so
you can inspect values during development / troubleshooting.

Safety:
  * bodies are passed through :func:`redact` (universal + project sensitive keys)
    so secrets are hidden as ``[REDACTED]`` (or ``4242***4242`` for partial keys)
    — unless ``redact_enabled=False`` (``LOG_REDACT=false``), a local-only escape
    hatch to inspect raw values while debugging;
  * output is truncated to ``max_bytes`` to keep log lines small;
  * only JSON bodies are rendered; other content types log a size placeholder;
  * ``/health`` is skipped.

Implemented as **pure ASGI** middleware (not ``BaseHTTPMiddleware``) so it
observes body chunks as they flow without consuming the stream — it never
breaks request parsing or the response.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterable

from app.utils.redact import redact

logger = logging.getLogger("http.body")

_SKIP_PATHS = frozenset({"/health"})


def _header(headers: Iterable[tuple[bytes, bytes]], name: bytes) -> str:
    for key, value in headers:
        if key.lower() == name:
            return value.decode("latin-1")
    return ""


def _render(
    raw: bytes,
    content_type: str,
    max_bytes: int,
    extra_keys: frozenset[str],
    partial_keys: frozenset[str],
    redact_enabled: bool,
) -> str | None:
    if not raw:
        return None
    if "application/json" in content_type:
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if data is not None:
            if redact_enabled:
                data = redact(data, extra_keys=extra_keys, partial_keys=partial_keys)
            text = json.dumps(data, ensure_ascii=False)
            if len(text) > max_bytes:
                return text[:max_bytes] + "…(truncated)"
            return text
    return f"<{len(raw)} bytes {content_type or 'unknown'}>"


class BodyLogMiddleware:
    def __init__(
        self,
        app,
        *,
        max_bytes: int,
        extra_keys: frozenset[str],
        partial_keys: frozenset[str] = frozenset(),
        redact_enabled: bool = True,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.extra_keys = extra_keys
        self.partial_keys = partial_keys
        self.redact_enabled = redact_enabled
        # Stop buffering well before memory blows up on large/streaming bodies.
        self._cap = max_bytes * 4

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http" or scope.get("path") in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        req_buf = bytearray()

        async def receive_wrapper() -> dict:
            message = await receive()
            if message["type"] == "http.request" and len(req_buf) < self._cap:
                req_buf.extend(message.get("body", b""))
            return message

        res_buf = bytearray()
        captured: dict[str, str] = {"content_type": ""}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                captured["content_type"] = _header(message.get("headers", []), b"content-type")
            elif message["type"] == "http.response.body" and len(res_buf) < self._cap:
                res_buf.extend(message.get("body", b""))
            await send(message)

        await self.app(scope, receive_wrapper, send_wrapper)

        req_ctype = _header(scope.get("headers", []), b"content-type")
        req_body = _render(
            bytes(req_buf), req_ctype, self.max_bytes,
            self.extra_keys, self.partial_keys, self.redact_enabled,
        )
        res_body = _render(
            bytes(res_buf), captured["content_type"], self.max_bytes,
            self.extra_keys, self.partial_keys, self.redact_enabled,
        )

        logger.info(
            "%s %s request=%s response=%s",
            scope.get("method", "-"),
            scope.get("path", "-"),
            req_body,
            res_body,
            extra={"request_body": req_body, "response_body": res_body},
        )
