"""Auth route definitions — examples, dev token minting, permission catalog."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.internal.auth.delivery.http.dependencies import AuthGuard, _bearer
from app.internal.auth.delivery.http.dto.example import MeResponse, PublicStatusResponse
from app.internal.auth.delivery.http.dto.token import IssueTokenRequest, IssueTokenResponse
from app.internal.auth.delivery.http.handler import AuthHandler
from app.utils.openapi import ErrorEnvelope, SuccessEnvelope

_UNAUTHORIZED = {401: {"model": ErrorEnvelope, "description": "Missing or invalid JWT"}}


def register_routes(
    handler: AuthHandler,
    auth: AuthGuard,
    *,
    dev_token_enabled: bool,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    @router.get(
        "/public",
        summary="Public status (no auth)",
        description=(
            "**Example — no authentication.** Callable without an ``Authorization`` header."
        ),
        response_model=SuccessEnvelope[PublicStatusResponse],
    )
    async def public_status():
        return await handler.public_status()

    @router.get(
        "/me",
        summary="Current caller from JWT (auth required)",
        description=(
            "**Example — authentication required.** Send ``Authorization: Bearer <token>``. "
            "Any valid JWT is accepted; no specific permission is required."
        ),
        response_model=SuccessEnvelope[MeResponse],
        responses=_UNAUTHORIZED,
    )
    async def get_me(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    ):
        return await handler.me(auth.resolve_user(credentials))

    @router.get(
        "/permissions",
        summary="List permissions and allowed routes (no auth)",
        description=(
            "**Example — no authentication.** Reference table of JWT permission claims."
        ),
        response_model=SuccessEnvelope[dict[str, str]],
    )
    async def list_permissions():
        return await handler.list_permissions()

    if dev_token_enabled:

        @router.post(
            "/token",
            status_code=201,
            summary="Issue a dev JWT (no auth)",
            description=(
                "**Example — no authentication.** Mint a signed JWT for Swagger / local testing. "
                "Disable in production via ``AUTH_DEV_TOKEN_ENABLED=false``."
            ),
            response_model=SuccessEnvelope[IssueTokenResponse],
        )
        async def issue_token(req: IssueTokenRequest):
            return await handler.issue_token(req)

    return router
