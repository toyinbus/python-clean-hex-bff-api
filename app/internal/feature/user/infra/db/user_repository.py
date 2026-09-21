"""User repository — mocked in-memory implementation.

This is the driven adapter that satisfies ``port.UserRepository``. In a real
service this would run SQL via an async driver / ORM; here it keeps rows in a
dict so the demo runs with zero external infrastructure.

It still follows the production contract:
  * maps DB models <-> domain entities at the boundary (never leaks models);
  * translates "missing row" into the domain error ``NotFoundError`` so the
    usecase never sees infrastructure-specific errors;
  * honours the pagination filter (search / status / sort / limit / offset).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
)
from app.internal.feature.user.domain.port.user import ListUsersFilter, UserRepository
from app.internal.feature.user.infra.db.model.user import UserModel
from app.utils import apperror

_SORTABLE_COLUMNS = ("id", "name", "email", "status", "created_at", "updated_at")


def _seed_rows() -> dict[int, UserModel]:
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=UTC)
    seed = [
        UserModel(1, "Alice Nguyen", "alice@example.com", "active", base, base),
        UserModel(2, "Bruno Costa", "bruno@example.com", "inactive", base, base),
        UserModel(3, "Chen Wei", "chen@example.com", "suspended", base, base),
    ]
    return {row.id: row for row in seed}


class UserRepositoryImpl(UserRepository):
    def __init__(self) -> None:
        self._rows: dict[int, UserModel] = _seed_rows()
        self._next_id: int = max(self._rows, default=0) + 1
        self._lock = asyncio.Lock()

    async def list(self, filter: ListUsersFilter) -> ListUsersResult:
        q = filter.query.normalize()

        rows = list(self._rows.values())

        if filter.status:
            rows = [r for r in rows if r.status == filter.status]
        if q.search:
            needle = q.search.casefold()
            rows = [
                r for r in rows
                if needle in r.name.casefold() or needle in r.email.casefold()
            ]

        total = len(rows)
        rows = self._sort(rows, q.order_clause("id ASC", *_SORTABLE_COLUMNS))
        window = rows[q.offset : q.offset + q.limit]

        return ListUsersResult(items=[r.to_domain() for r in window], total=total)

    async def get_by_id(self, user_id: int) -> User:
        row = self._rows.get(user_id)
        if row is None:
            raise apperror.NotFoundError("user not found")
        return row.to_domain()

    async def get_by_email(self, email: str) -> User | None:
        for row in self._rows.values():
            if row.email.casefold() == email.casefold():
                return row.to_domain()
        return None

    async def create(self, params: CreateUserParams) -> User:
        async with self._lock:
            now = datetime.now(UTC)
            model = UserModel.from_params(self._next_id, params, now)
            self._rows[model.id] = model
            self._next_id += 1
            return model.to_domain()

    async def update(self, params: UpdateUserParams) -> User:
        async with self._lock:
            row = self._rows.get(params.id)
            if row is None:
                raise apperror.NotFoundError("user not found")
            updated = row.with_updates(
                name=params.name,
                email=params.email,
                status=params.status,
                now=datetime.now(UTC),
            )
            self._rows[params.id] = updated
            return updated.to_domain()

    async def delete(self, user_id: int) -> None:
        async with self._lock:
            if user_id not in self._rows:
                raise apperror.NotFoundError("user not found")
            del self._rows[user_id]

    @staticmethod
    def _sort(rows: list[UserModel], order_clause: str) -> list[UserModel]:
        column, _, direction = order_clause.partition(" ")
        reverse = direction.upper() == "DESC"
        return sorted(rows, key=lambda r: getattr(r, column), reverse=reverse)
