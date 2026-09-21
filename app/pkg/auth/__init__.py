"""Project-specific auth contracts (permissions, authenticated user)."""

from app.pkg.auth.authenticated_user import AuthenticatedUser
from app.pkg.auth.permissions import Permission, permission_descriptions

__all__ = ["AuthenticatedUser", "Permission", "permission_descriptions"]
