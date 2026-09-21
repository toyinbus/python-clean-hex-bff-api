"""OpenAPI documentation helpers (generic, reusable).

These models exist ONLY to describe the standard response envelope in the
OpenAPI schema (Swagger UI / ReDoc). Handlers still build the real envelope via
``app.utils.response`` and return ``JSONResponse`` directly — returning a
``Response`` instance bypasses ``response_model`` serialization, so attaching
these models to routes is **documentation-only** and never alters runtime
behaviour.

Usage on a route::

    @router.get(
        "/{user_id}",
        response_model=SuccessEnvelope[UserResponse],
        responses={404: {"model": ErrorEnvelope}},
    )
    async def get_user(...): ...
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class SuccessEnvelope(BaseModel, Generic[T]):
    """Success response envelope (mirrors ``response_success``)."""

    success: bool = True
    status: str = "ok"
    code: str = "00000"
    data: T | None = None
    request_id: str | None = None


class ErrorEnvelope(BaseModel):
    """Error response envelope (mirrors ``response_error``)."""

    success: bool = False
    code: str = "10004"
    message: str = "resource not found"
    request_id: str | None = None
