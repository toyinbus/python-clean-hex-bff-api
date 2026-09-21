"""HTTP middleware that assigns a request id to every request.

Mirrors the Go `httplog` middleware behaviour: it reads an inbound
``X-Request-Id`` (or generates one), stores it in the request-scoped
ContextVar so response builders can stamp it, and echoes it back on the
response header for tracing.
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.request_context import set_request_id

REQUEST_ID_HEADER = "X-Request-Id"


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
