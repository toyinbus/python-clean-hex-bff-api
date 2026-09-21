"""Auth HTTP handlers."""

from __future__ import annotations

from http import HTTPStatus

from fastapi.responses import JSONResponse

from app.internal.auth.delivery.http.dto.example import MeResponse, PublicStatusResponse
from app.internal.auth.delivery.http.dto.token import IssueTokenRequest, IssueTokenResponse
from app.internal.auth.domain.port.token_validator import TokenValidator
from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import permission_descriptions
from app.utils.response import response_success


class AuthHandler:
    def __init__(
        self,
        validator: TokenValidator,
        *,
        default_expire_minutes: int,
    ) -> None:
        self._validator = validator
        self._default_expire_minutes = default_expire_minutes

    async def issue_token(self, req: IssueTokenRequest) -> JSONResponse:
        perms = frozenset(req.permissions)
        ttl = req.expire_minutes if req.expire_minutes is not None else self._default_expire_minutes
        token = self._validator.issue(
            subject=req.subject,
            permissions=perms,
            expire_minutes=ttl,
        )
        body = IssueTokenResponse(
            access_token=token,
            expires_in_minutes=ttl,
            permissions=sorted(p.value for p in perms),
        )
        return response_success(
            body.model_dump(mode="json"),
            http_code=HTTPStatus.CREATED,
        )

    async def list_permissions(self) -> JSONResponse:
        return response_success(permission_descriptions())

    async def public_status(self) -> JSONResponse:
        body = PublicStatusResponse(
            message="This endpoint is public — no Bearer token required.",
        )
        return response_success(body.model_dump(mode="json"))

    async def me(self, user: AuthenticatedUser) -> JSONResponse:
        body = MeResponse(
            user_id=user.user_id,
            permissions=sorted(p.value for p in user.permissions),
        )
        return response_success(body.model_dump(mode="json"))
