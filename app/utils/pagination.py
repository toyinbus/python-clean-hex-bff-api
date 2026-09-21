"""Shared pagination + free-text search + sorting primitives.

Generic, domain-agnostic value object — knows nothing about this project's
business, so it lives in ``utils`` (the reusable library layer). Feature-specific
filter objects embed :class:`Query` (see the ``port`` layer) and call
:meth:`Query.normalize` before use.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True)
class Query:
    """Pagination + search + sorting parameters (pure value object)."""

    search: str = ""
    limit: int = 0
    offset: int = 0
    sort_by: str = ""
    sort_order: str = ""

    def normalize(self) -> "Query":
        """Return a copy with safe defaults applied."""
        limit = self.limit
        if limit <= 0:
            limit = DEFAULT_LIMIT
        if limit > MAX_LIMIT:
            limit = MAX_LIMIT

        offset = self.offset if self.offset >= 0 else 0

        sort_order = self.sort_order.strip().upper()
        if sort_order not in ("ASC", "DESC"):
            sort_order = ""

        return replace(self, limit=limit, offset=offset, sort_order=sort_order)

    def order_clause(self, fallback: str, *allowed_columns: str) -> str:
        """Return a safe ORDER BY expression.

        If a valid ``sort_by`` was provided and it exists in ``allowed_columns``
        it is used; otherwise ``fallback`` is returned as-is.
        """
        col = self.sort_by.strip()
        if not col:
            return fallback
        for c in allowed_columns:
            if col.casefold() == c.casefold():
                direction = self.sort_order or "ASC"
                return f"{c} {direction}"
        return fallback
