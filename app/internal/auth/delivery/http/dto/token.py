"""Auth DTOs — dev token minting only."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.pkg.auth.permissions import Permission


class IssueTokenRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=128, examples=["1"])
    permissions: list[Permission] = Field(
        ...,
        min_length=1,
        examples=[[Permission.USER_READ, Permission.USER_CREATE]],
    )
    expire_minutes: int | None = Field(
        default=None,
        ge=1,
        le=24 * 60,
        description="Override default JWT expiry (minutes).",
    )


class IssueTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    permissions: list[str]
