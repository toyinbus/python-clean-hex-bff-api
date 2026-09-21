"""Token validation port — secondary (driven) adapter contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import Permission


@dataclass(frozen=True)
class TokenPayload:
    """Raw claims extracted from a JWT before mapping to :class:`AuthenticatedUser`."""

    subject: str
    permissions: frozenset[Permission]
    expires_at: datetime | None


class TokenValidator(ABC):
    """Validate bearer tokens and map them to domain identity."""

    @abstractmethod
    def validate(self, token: str) -> AuthenticatedUser:
        """Parse and verify a JWT. Raises :class:`UnauthorizedError` on failure."""

    @abstractmethod
    def issue(
        self,
        *,
        subject: str,
        permissions: frozenset[Permission],
        expire_minutes: int | None = None,
    ) -> str:
        """Mint a signed JWT (dev / test helper)."""
