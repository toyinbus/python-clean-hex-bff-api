"""Standard JSON response envelope.

Mirrors the Go `utils.ResponseSuccess` / `utils.ResponseError`. Every response
body carries ``success``, a 5-digit ``code`` and (when known) ``request_id``.
Only the human-readable ``message`` — never a raw exception — is sent to the
client; the original error is logged separately.

Success: {"success": true,  "status": "ok", "code": "00000", "data": {...}, "request_id": "..."}
Error:   {"success": false, "code": "10004", "message": "...", "request_id": "..."}
"""

from __future__ import annotations

import logging
from http import HTTPStatus
from typing import Any

from fastapi.responses import JSONResponse

from app.utils import apperror
from app.utils.request_context import get_request_id

logger = logging.getLogger("python-clean-hex-bff-api")


def response_success(
    data: Any = None,
    *,
    http_code: int = HTTPStatus.OK,
    status: str = "ok",
    code: str = "",
    message: str = "",
) -> JSONResponse:
    """Write a JSON success response. Status defaults to "ok", code to "00000"."""
    body: dict[str, Any] = {
        "success": True,
        "status": status or "ok",
        "code": code or apperror.CODE_OK,
    }
    if message:
        body["message"] = message
    if data is not None:
        body["data"] = data
    rid = get_request_id()
    if rid:
        body["request_id"] = rid
    return JSONResponse(status_code=http_code, content=body)


def response_error(
    *,
    http_code: int = HTTPStatus.BAD_REQUEST,
    message: str,
    code: str = "",
    err: Exception | None = None,
    data: Any = None,
) -> JSONResponse:
    """Write a JSON error response with a resolved 5-digit code.

    The underlying ``err`` (if any) is logged but never leaked to the client.
    """
    resolved_code = apperror.resolve_error_code(code, err, http_code)

    if err is not None:
        # Tag every line with the HTTP status + 5-digit code (visible in the
        # console message, and as separate fields in JSON for filtering).
        # 5xx = unexpected server fault -> ERROR with stack trace.
        # 4xx = expected client/business outcome (404, 409, 401, ...) -> WARNING,
        #       no stack trace, so normal outcomes don't spam logs or trip alerts.
        extra = {"status": http_code, "code": resolved_code}
        if http_code >= HTTPStatus.INTERNAL_SERVER_ERROR:
            logger.error(
                "http error [%s %s]: %s", http_code, resolved_code, err,
                exc_info=err, extra=extra,
            )
        else:
            logger.warning(
                "http error [%s %s]: %s", http_code, resolved_code, err, extra=extra
            )

    body: dict[str, Any] = {
        "success": False,
        "code": resolved_code,
        "message": message,
    }
    if data is not None:
        body["data"] = data
    rid = get_request_id()
    if rid:
        body["request_id"] = rid
    return JSONResponse(status_code=http_code, content=body)
