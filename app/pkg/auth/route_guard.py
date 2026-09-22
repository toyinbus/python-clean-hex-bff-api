"""Route-level auth guard contract — shared by features without cross-feature imports."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from app.pkg.auth.permissions import Permission


class RouteAuthGuard(Protocol):
    """Minimal surface a feature route module needs from the auth feature."""

    def require_permissions(self, *required: Permission) -> Callable[..., None]: ...
