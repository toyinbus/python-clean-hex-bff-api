"""JWT token validator — HS256 adapter for :class:`TokenValidator`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.internal.auth.domain.port.token_validator import TokenValidator
from app.pkg import error_codes
from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import Permission
from app.utils.apperror import BadRequestError, UnauthorizedError

_KNOWN_PERMISSIONS = frozenset(Permission)


class JwtTokenValidatorImpl(TokenValidator):
    def __init__(
        self,
        *,
        secret: str,
        algorithm: str,
        default_expire_minutes: int,
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._default_expire_minutes = default_expire_minutes

    def validate(self, token: str) -> AuthenticatedUser:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError(
                "token expired",
                code=error_codes.AUTH_TOKEN_EXPIRED,
            ) from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError(
                "invalid token",
                code=error_codes.AUTH_TOKEN_INVALID,
            ) from exc

        subject = payload.get("sub")
        if not subject or not isinstance(subject, str):
            raise UnauthorizedError(
                "invalid token subject",
                code=error_codes.AUTH_TOKEN_INVALID,
            )

        raw_permissions = payload.get("permissions", [])
        if not isinstance(raw_permissions, list):
            raise UnauthorizedError(
                "invalid token permissions",
                code=error_codes.AUTH_TOKEN_INVALID,
            )

        permissions: set[Permission] = set()
        for value in raw_permissions:
            if not isinstance(value, str):
                continue
            try:
                perm = Permission(value)
            except ValueError:
                continue
            permissions.add(perm)

        return AuthenticatedUser(user_id=subject, permissions=frozenset(permissions))

    def issue(
        self,
        *,
        subject: str,
        permissions: frozenset[Permission],
        expire_minutes: int | None = None,
    ) -> str:
        unknown = permissions - _KNOWN_PERMISSIONS
        if unknown:
            names = ", ".join(sorted(p.value for p in unknown))
            raise BadRequestError(f"unknown permissions: {names}")

        ttl = expire_minutes if expire_minutes is not None else self._default_expire_minutes
        now = datetime.now(tz=UTC)
        payload = {
            "sub": subject,
            "permissions": sorted(p.value for p in permissions),
            "iat": now,
            "exp": now + timedelta(minutes=ttl),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)
