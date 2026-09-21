"""App-wide async database pool holder (project-specific shared infra).

Why a holder instead of passing a pool straight into the repository?
Construction of the DI object graph is **synchronous** (it happens at import
time when routes are mounted), but opening an ``asyncpg`` pool is **async** and
must run inside the FastAPI lifespan. So repositories receive this holder at
construction time and read ``.pool`` lazily at query time; the pool itself is
created — and health-checked — once at startup.

Only used when ``STORAGE_TYPE=postgres``. ``asyncpg`` is imported lazily inside
:meth:`connect`, so the default in-memory demo needs neither the driver nor a
running database.
"""

from __future__ import annotations

from typing import Any


class Database:
    """Holds the process-wide connection pool (populated at startup)."""

    def __init__(self) -> None:
        self._pool: Any | None = None

    @property
    def pool(self) -> Any:
        if self._pool is None:
            raise RuntimeError(
                "database pool is not initialized — this repository requires "
                "STORAGE_TYPE=postgres and a successful startup connection."
            )
        return self._pool

    async def connect(
        self,
        *,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        min_size: int,
        max_size: int,
        timeout: int,
    ) -> None:
        """Open the pool and immediately ping it (fail-fast on startup).

        Any connection error propagates so the application refuses to start.
        """
        import asyncpg  # lazy: only needed for the postgres backend

        self._pool = await asyncpg.create_pool(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            min_size=min_size,
            max_size=max_size,
            timeout=timeout,
        )
        await self.ping()

    async def ping(self) -> None:
        """Lightweight liveness probe (``SELECT 1``)."""
        async with self._pool.acquire() as conn:  # type: ignore[union-attr]
            await conn.execute("SELECT 1")

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
