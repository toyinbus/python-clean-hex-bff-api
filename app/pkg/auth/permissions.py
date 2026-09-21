"""Permission registry — which JWT permission grants access to which routes.

Each permission is a string claim inside the JWT ``permissions`` array.
Routes declare the required permission via :class:`AuthGuard` dependencies.

| Permission       | Routes                         | Description                    |
|------------------|--------------------------------|--------------------------------|
| ``user:read``    | GET /users, GET /users/{id}    | List and view users            |
| ``user:create``  | POST /users                    | Create a new user              |
| ``user:update``  | PUT /users/{id}                | Update an existing user        |
| ``user:delete``  | DELETE /users/{id}             | Delete a user                  |
"""

from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    USER_READ = "user:read"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"


def permission_descriptions() -> dict[str, str]:
    """Human-readable descriptions keyed by permission value."""
    return {
        Permission.USER_READ: "List and view users (GET /users, GET /users/{id})",
        Permission.USER_CREATE: "Create users (POST /users)",
        Permission.USER_UPDATE: "Update users (PUT /users/{id})",
        Permission.USER_DELETE: "Delete users (DELETE /users/{id})",
    }
