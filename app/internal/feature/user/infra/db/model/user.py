"""DB model for the users table (Frameworks & Drivers layer).

Mirrors the Go ``infra/db/model`` layer: the model is the persistence-shaped
struct, and mapping to/from the pure domain entity happens here — never inline
in the repository. In a real service this would carry ORM/column metadata; the
demo keeps it a plain dataclass because the repository is mocked in-memory.

Mapping rules (see ARCHITECTURE.md § Schema vs Entity vs dbModel):
  * ``to_domain()``   : model -> entity (used on SELECT)
  * ``from_params()`` : write DTO/params -> model (used on INSERT/UPDATE)
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from app.internal.feature.user.domain.entity.user import CreateUserParams, User


@dataclass
class UserModel:
    id: int
    name: str
    email: str
    status: str
    created_at: datetime
    updated_at: datetime

    def to_domain(self) -> User:
        """Map persistence model -> pure domain entity."""
        return User(
            id=self.id,
            name=self.name,
            email=self.email,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def from_params(new_id: int, params: CreateUserParams, now: datetime) -> "UserModel":
        """Build a persistence model from create params (INSERT boundary)."""
        return UserModel(
            id=new_id,
            name=params.name,
            email=params.email,
            status=params.status,
            created_at=now,
            updated_at=now,
        )

    def with_updates(
        self,
        *,
        name: str | None,
        email: str | None,
        status: str | None,
        now: datetime,
    ) -> "UserModel":
        """Return a copy with the provided non-None fields applied (UPDATE boundary)."""
        return replace(
            self,
            name=self.name if name is None else name,
            email=self.email if email is None else email,
            status=self.status if status is None else status,
            updated_at=now,
        )
