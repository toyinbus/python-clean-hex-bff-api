"""User repository — PostgreSQL implementation (reference driven adapter).

Satisfies the same ``port.UserRepository`` contract as the in-memory mock, so
switching backends never touches the usecase or handler — only the DI wiring in
``set.py`` (selected by ``STORAGE_TYPE``). Selected only when
``STORAGE_TYPE=postgres``; the pool is opened and health-checked at startup
(fail-fast) by ``app.main``'s lifespan.

Follows the production contract:
  * maps DB rows <-> domain entities via ``UserModel`` (never leaks rows);
  * translates "missing row" into ``NotFoundError`` so the usecase only sees
    domain errors;
  * honours the pagination filter (search / status / sort / limit / offset),
    reusing the whitelisted ``order_clause`` for safe sorting.

Assumes a ``users`` table::

    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
)
from app.internal.feature.user.domain.port.user import ListUsersFilter, UserRepository
from app.internal.feature.user.infra.db.model.user import UserModel
from app.pkg.database import Database
from app.utils import apperror

_COLUMNS = "id, name, email, status, created_at, updated_at"
_SORTABLE_COLUMNS = ("id", "name", "email", "status", "created_at", "updated_at")


class UserRepositoryPostgres(UserRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    @staticmethod
    def _to_model(row: Any) -> UserModel:
        return UserModel(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    async def list(self, filter: ListUsersFilter) -> ListUsersResult:
        q = filter.query.normalize()

        conditions: list[str] = []
        args: list[Any] = []
        if filter.status:
            args.append(filter.status)
            conditions.append(f"status = ${len(args)}")
        if q.search:
            args.append(f"%{q.search}%")
            conditions.append(f"(name ILIKE ${len(args)} OR email ILIKE ${len(args)})")
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        order_sql = q.order_clause("id ASC", *_SORTABLE_COLUMNS)  # whitelisted -> safe

        limit_ph, offset_ph = f"${len(args) + 1}", f"${len(args) + 2}"

        async with self._db.pool.acquire() as conn:
            total = await conn.fetchval(f"SELECT count(*) FROM users {where_sql}", *args)
            rows = await conn.fetch(
                f"SELECT {_COLUMNS} FROM users {where_sql} "
                f"ORDER BY {order_sql} LIMIT {limit_ph} OFFSET {offset_ph}",
                *args,
                q.limit,
                q.offset,
            )

        items = [self._to_model(r).to_domain() for r in rows]
        return ListUsersResult(items=items, total=int(total or 0))

    async def get_by_id(self, user_id: int) -> User:
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(f"SELECT {_COLUMNS} FROM users WHERE id = $1", user_id)
        if row is None:
            raise apperror.NotFoundError("user not found")
        return self._to_model(row).to_domain()

    async def get_by_email(self, email: str) -> User | None:
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT {_COLUMNS} FROM users WHERE lower(email) = lower($1)", email
            )
        return self._to_model(row).to_domain() if row is not None else None

    async def create(self, params: CreateUserParams) -> User:
        now = datetime.now(UTC)
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO users (name, email, status, created_at, updated_at) "
                f"VALUES ($1, $2, $3, $4, $4) RETURNING {_COLUMNS}",
                params.name,
                params.email,
                params.status,
                now,
            )
        return self._to_model(row).to_domain()

    async def update(self, params: UpdateUserParams) -> User:
        now = datetime.now(UTC)
        async with self._db.pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE users SET "
                "name = COALESCE($2, name), "
                "email = COALESCE($3, email), "
                "status = COALESCE($4, status), "
                "updated_at = $5 "
                f"WHERE id = $1 RETURNING {_COLUMNS}",
                params.id,
                params.name,
                params.email,
                params.status,
                now,
            )
        if row is None:
            raise apperror.NotFoundError("user not found")
        return self._to_model(row).to_domain()

    async def delete(self, user_id: int) -> None:
        async with self._db.pool.acquire() as conn:
            status = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        # asyncpg returns a command tag like "DELETE 1"; "DELETE 0" == no row.
        if status.rsplit(" ", 1)[-1] == "0":
            raise apperror.NotFoundError("user not found")
