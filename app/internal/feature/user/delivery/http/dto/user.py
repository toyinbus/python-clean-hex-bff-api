"""HTTP DTOs for the user feature (Interface Adapters layer).

Pydantic models — the FastAPI-idiomatic equivalent of the Go ``dto`` package.
One file per entity holds BOTH requests and responses.

CleanHex rules:
  * Request DTOs perform format validation only and DO NOT import the entity.
    The handler extracts values and builds ``entity.*Params``.
  * Response DTOs import the entity for the ``from_entity`` factory functions
    (standalone functions, not methods) which only format/transform data.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.internal.feature.user.domain.entity.user import User
from app.internal.feature.user.domain.port.user import ListUsersFilter, UserStatus
from app.utils.pagination import Query

# ── Requests ───────────────────────────────────────────────────────────────────


class ListUsersQuery(BaseModel):
    """Query-string params for the list endpoint."""

    search: str = ""
    status: str = ""
    limit: int = 0
    offset: int = 0
    sort_by: str = ""
    sort_order: str = ""

    def to_filter(self) -> ListUsersFilter:
        return ListUsersFilter(
            query=Query(
                search=self.search,
                limit=self.limit,
                offset=self.offset,
                sort_by=self.sort_by,
                sort_order=self.sort_order,
            ),
            status=self.status,
        )


class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Alice Nguyen"])
    email: EmailStr = Field(examples=["alice@example.com"])
    status: UserStatus = Field(default=UserStatus.ACTIVE, examples=[UserStatus.ACTIVE])


class UpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    email: EmailStr | None = None
    status: UserStatus | None = None


# ── Responses ──────────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    status: str
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    limit: int
    offset: int


def user_response_from_entity(user: User) -> UserResponse:
    """Standalone factory: entity -> response DTO (format/transform only)."""
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        status=user.status,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def user_responses_from_entities(users: list[User]) -> list[UserResponse]:
    return [user_response_from_entity(u) for u in users]
