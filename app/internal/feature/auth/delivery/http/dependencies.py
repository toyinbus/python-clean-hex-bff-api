"""FastAPI dependencies for JWT authentication and permission checks."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.internal.feature.auth.domain.port.token_validator import TokenValidator
from app.pkg import error_codes
from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import Permission
from app.utils.apperror import ForbiddenError, UnauthorizedError

_bearer = HTTPBearer(auto_error=False)

# Bypass identity used when AUTH_ENABLED=false (tests / local dev).
_DEV_USER = AuthenticatedUser(
    user_id="dev",
    permissions=frozenset(Permission),
)


class AuthGuard:
    """Route-level JWT guard — inject via DI, attach permissions per endpoint."""

    def __init__(self, validator: TokenValidator, *, auth_enabled: bool = True) -> None:
        self._validator = validator
        self._auth_enabled = auth_enabled
        self.get_current_user: Callable[..., AuthenticatedUser] = self._build_get_current_user()

    def resolve_user(
        self,
        credentials: HTTPAuthorizationCredentials | None,
    ) -> AuthenticatedUser:
        if not self._auth_enabled:
            return _DEV_USER

        if credentials is None or credentials.scheme.lower() != "bearer":
            raise UnauthorizedError(
                "missing bearer token",
                code=error_codes.AUTH_TOKEN_MISSING,
            )

        token = credentials.credentials.strip()
        if not token:
            raise UnauthorizedError(
                "missing bearer token",
                code=error_codes.AUTH_TOKEN_MISSING,
            )

        return self._validator.validate(token)

    def _build_get_current_user(self) -> Callable[..., AuthenticatedUser]:
        guard = self

        async def get_current_user(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        ) -> AuthenticatedUser:
            return guard.resolve_user(credentials)

        return get_current_user

    def require_permissions(self, *required: Permission) -> Callable[..., None]:
        """Factory returning a route dependency that enforces ALL listed permissions."""
        guard = self

        async def check_permissions(
            credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
        ) -> None:
            user = guard.resolve_user(credentials)
            if not guard._auth_enabled:
                return
            if not user.has_all_permissions(*required):
                missing = ", ".join(p.value for p in required if p not in user.permissions)
                raise ForbiddenError(
                    f"insufficient permission: requires {missing}",
                    code=error_codes.AUTH_INSUFFICIENT_PERMISSION,
                )

        return check_permissions
