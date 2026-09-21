"""Request-scoped context (request id) propagated via a ContextVar.

Mirrors the Go `httplog.RequestID(ctx)` helper: the middleware assigns an id
per request and the response builders read it back to stamp every envelope.
"""

from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def get_request_id() -> str:
    return _request_id.get()
