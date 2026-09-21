"""Structured access-log middleware.

One line per request: method, path, status, latency. Replaces uvicorn's default
access log (silenced in ``app.main``) so every line also carries latency plus
structured ``status`` / ``latency_ms`` fields that ship cleanly to CloudWatch /
Elastic. The request id is stamped automatically by the logging filter.

It sits *inside* ``RequestContextMiddleware`` (added first, so it is the inner
layer) so the request-id ContextVar is already set when it logs. Health checks
are skipped to avoid noise from readiness probes.
"""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("access")

_SKIP_PATHS = frozenset({"/health"})


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)

        path = request.url.path
        if path not in _SKIP_PATHS:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "%s %s -> %s (%.2fms)",
                request.method,
                path,
                response.status_code,
                latency_ms,
                extra={
                    "http_method": request.method,
                    "path": path,
                    "status": response.status_code,
                    "latency_ms": latency_ms,
                },
            )
        return response
