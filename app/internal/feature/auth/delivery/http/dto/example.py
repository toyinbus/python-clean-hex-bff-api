"""Auth example DTOs — public vs protected route responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PublicStatusResponse(BaseModel):
    message: str
    auth_required: bool = False


class MeResponse(BaseModel):
    user_id: str
    permissions: list[str] = Field(
        ...,
        description="Permission claims from the JWT ``permissions`` array.",
    )
