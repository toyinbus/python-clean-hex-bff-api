"""Pure domain entities for the user feature.

Enterprise Business layer. These are plain dataclasses with NO framework
concerns — no pydantic, no ORM/serialization tags. They may hold self-contained
business rules (see :meth:`User.deactivate`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.utils import apperror


@dataclass
class User:
    """A platform user (pure domain object)."""

    id: int
    name: str
    email: str
    status: str  # see port.UserStatus for the allowed values
    created_at: datetime
    updated_at: datetime

    def can_be_deleted(self) -> bool:
        """A self-contained business rule (invariant protection)."""
        return self.status != "active"

    def deactivate(self) -> None:
        self.status = "inactive"


@dataclass
class CreateUserParams:
    name: str
    email: str
    status: str = "active"


@dataclass
class UpdateUserParams:
    """Partial update. ``None`` means "leave unchanged"."""

    id: int
    name: str | None = None
    email: str | None = None
    status: str | None = None


@dataclass
class ListUsersResult:
    """Paginated list result (pure domain value object)."""

    items: list[User] = field(default_factory=list)
    total: int = 0


def ensure_valid_email(email: str) -> None:
    """Domain invariant guard reused by usecase-level validation."""
    if "@" not in email:
        raise apperror.BadRequestError("email is not valid")
