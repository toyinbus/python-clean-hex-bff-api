"""Ports (interfaces) + domain value types for the user feature.

Interface Adapters layer. Ports are Abstract Base Classes — the Python
equivalent of Go interfaces. Concrete implementations live in ``usecase/``
(primary/driving) and ``infra/`` (secondary/driven) and are bound to these
ports in ``set.py`` (the DI equivalent of Go's ``wire.Bind``).

Domain value types (typed constants) live here, NOT in ``domain/entity`` —
port is the contract layer every other layer may import.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum

from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
)
from app.utils.pagination import Query


class UserStatus(StrEnum):
    """Domain value type — the allowed user statuses."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


@dataclass
class ListUsersFilter:
    """Filter for listing users. Embeds the shared pagination Query."""

    query: Query = field(default_factory=Query)
    status: str = ""


class UserRepository(ABC):
    """Secondary port — implemented by ``infra/db`` (driven adapter)."""

    @abstractmethod
    async def list(self, filter: ListUsersFilter) -> ListUsersResult: ...

    @abstractmethod
    async def get_by_id(self, user_id: int) -> User: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, params: CreateUserParams) -> User: ...

    @abstractmethod
    async def update(self, params: UpdateUserParams) -> User: ...

    @abstractmethod
    async def delete(self, user_id: int) -> None: ...


class UserUsecase(ABC):
    """Primary port — implemented by ``usecase`` and called by the handler."""

    @abstractmethod
    async def list(self, filter: ListUsersFilter) -> ListUsersResult: ...

    @abstractmethod
    async def get(self, user_id: int) -> User: ...

    @abstractmethod
    async def create(self, params: CreateUserParams) -> User: ...

    @abstractmethod
    async def update(self, params: UpdateUserParams) -> User: ...

    @abstractmethod
    async def delete(self, user_id: int) -> None: ...
