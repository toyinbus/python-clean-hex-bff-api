"""Feature contract for HTTP route registration.

Mirrors the Go `internal/server` package's ``HTTPRouteRegistrar`` interface.
Every feature exposes a ``Feature`` object (built in its ``set.py``) that knows
how to mount its own routes onto the shared API router. The composition root
(``app/di/container.py``) collects them and ``app/main.py`` registers each one —
exactly like Go's ``ProvideFeatures`` + ``ProvideHttpServer`` loop.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from fastapi import APIRouter


@runtime_checkable
class HTTPRouteRegistrar(Protocol):
    """A feature that can register its HTTP routes onto the shared API router."""

    def register_http(self, api: APIRouter) -> None: ...
