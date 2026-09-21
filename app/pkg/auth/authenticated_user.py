"""Authenticated caller extracted from a validated JWT."""

from __future__ import annotations

from dataclasses import dataclass

from app.pkg.auth.permissions import Permission


@dataclass(frozen=True)
class AuthenticatedUser:
    """Caller identity and permissions carried by the JWT."""

    user_id: str
    permissions: frozenset[Permission]

    def has_permission(self, permission: Permission) -> bool:
        return permission in self.permissions

    def has_all_permissions(self, *required: Permission) -> bool:
        return all(p in self.permissions for p in required)
