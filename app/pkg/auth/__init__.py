"""Project-specific auth contracts (permissions, authenticated user)."""

from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import Permission, permission_descriptions
from app.pkg.auth.route_guard import RouteAuthGuard

__all__ = ["AuthenticatedUser", "Permission", "RouteAuthGuard", "permission_descriptions"]
