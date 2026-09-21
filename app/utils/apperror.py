"""Generic domain-error mechanism + cross-cutting response codes.

This is the **reusable library layer** — it knows nothing about any particular
project's business. It provides:
  * :class:`AppError` and its subclasses (each with a default HTTP status + code),
  * the cross-cutting ``10xxx`` codes every service shares,
  * :func:`resolve_error_code` / :func:`default_code_from_status`.

Project-specific *domain* codes (e.g. "email already taken") do NOT live here —
they belong to the project's own registry at ``app/pkg/error_codes.py``. A feature
raises a generic subclass and passes the domain code:
``raise AlreadyExistsError("...", code=error_codes.USER_EMAIL_TAKEN)``.

Rules:
  * ``code`` is a permanent, append-only 5-digit string. Never reuse a number.
  * Frontends map ``code`` -> i18n. They MUST NOT string-match ``message``.
  * Repositories translate infrastructure errors into these domain errors.
  * Usecases raise/propagate these; handlers map them onto the HTTP envelope.
"""

from __future__ import annotations

from http import HTTPStatus

# ── Success ───────────────────────────────────────────────────────────────────
CODE_OK = "00000"

# ── Generic / cross-cutting (10xxx) ─────────────────────────────────────────────
CODE_INTERNAL = "10001"
CODE_BAD_REQUEST = "10002"
CODE_INVALID_INPUT = "10003"
CODE_NOT_FOUND = "10004"
CODE_ALREADY_EXISTS = "10005"
CODE_CONFLICT = "10006"
CODE_UNAUTHORIZED = "10007"
CODE_FORBIDDEN = "10008"
CODE_TOO_MANY_REQUESTS = "10009"

# Project-specific domain codes (20xxx auth, 30xxx billing, 70xxx user, ...) are
# NOT defined here — see app/pkg/error_codes.py.


class AppError(Exception):
    """Base domain error carrying an HTTP status and a stable 5-digit code."""

    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR
    code: str = CODE_INTERNAL

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        self.message = message or self.__class__.__name__
        if code is not None:
            self.code = code
        super().__init__(self.message)


class NotFoundError(AppError):
    http_status = HTTPStatus.NOT_FOUND
    code = CODE_NOT_FOUND


class AlreadyExistsError(AppError):
    http_status = HTTPStatus.CONFLICT
    code = CODE_ALREADY_EXISTS


class ConflictError(AppError):
    http_status = HTTPStatus.CONFLICT
    code = CODE_CONFLICT


class BadRequestError(AppError):
    http_status = HTTPStatus.BAD_REQUEST
    code = CODE_BAD_REQUEST


class InvalidInputError(AppError):
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY
    code = CODE_INVALID_INPUT


class UnauthorizedError(AppError):
    http_status = HTTPStatus.UNAUTHORIZED
    code = CODE_UNAUTHORIZED


class ForbiddenError(AppError):
    http_status = HTTPStatus.FORBIDDEN
    code = CODE_FORBIDDEN


class InternalError(AppError):
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR
    code = CODE_INTERNAL


_STATUS_TO_CODE: dict[int, str] = {
    HTTPStatus.OK: CODE_OK,
    HTTPStatus.CREATED: CODE_OK,
    HTTPStatus.NO_CONTENT: CODE_OK,
    HTTPStatus.BAD_REQUEST: CODE_BAD_REQUEST,
    HTTPStatus.UNAUTHORIZED: CODE_UNAUTHORIZED,
    HTTPStatus.FORBIDDEN: CODE_FORBIDDEN,
    HTTPStatus.NOT_FOUND: CODE_NOT_FOUND,
    HTTPStatus.CONFLICT: CODE_CONFLICT,
    HTTPStatus.UNPROCESSABLE_ENTITY: CODE_INVALID_INPUT,
    HTTPStatus.TOO_MANY_REQUESTS: CODE_TOO_MANY_REQUESTS,
}


def default_code_from_status(http_status: int) -> str:
    """Map an HTTP status to a generic 10xxx code when no specific one is set."""
    if http_status in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[http_status]
    if http_status >= 500:
        return CODE_INTERNAL
    if http_status >= 400:
        return CODE_BAD_REQUEST
    return CODE_OK


def resolve_error_code(explicit: str, err: Exception | None, http_status: int) -> str:
    """Pick the code that goes on the JSON envelope.

    Priority: explicit handler code -> the error's own code -> generic from status.
    """
    if explicit:
        return explicit
    if isinstance(err, AppError):
        return err.code
    return default_code_from_status(http_status)
