"""User route definitions.

Mirrors the Go ``delivery/http/route.go``: given a fully-constructed handler,
build an :class:`APIRouter` and bind each path to a handler method. The router
is mounted onto the shared API group by the feature object in ``set.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.internal.feature.user.delivery.http.dto.user import (
    CreateUserRequest,
    ListUsersQuery,
    UpdateUserRequest,
    UserListResponse,
    UserResponse,
)
from app.internal.feature.user.delivery.http.handler import UserHandler
from app.utils.openapi import ErrorEnvelope, SuccessEnvelope

# Shared error-envelope docs (documentation-only; handlers return JSONResponse).
_NOT_FOUND = {404: {"model": ErrorEnvelope, "description": "User not found"}}
_CONFLICT = {409: {"model": ErrorEnvelope, "description": "Conflicting state"}}


def register_routes(handler: UserHandler) -> APIRouter:
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get(
        "",
        summary="List users",
        description="Paginated, searchable list of users.",
        response_model=SuccessEnvelope[UserListResponse],
    )
    async def list_users(query: Annotated[ListUsersQuery, Query()]):
        return await handler.list(query)

    @router.get(
        "/{user_id}",
        summary="Get a user by ID",
        response_model=SuccessEnvelope[UserResponse],
        responses=_NOT_FOUND,
    )
    async def get_user(user_id: Annotated[int, Path(ge=1)]):
        return await handler.get(user_id)

    @router.post(
        "",
        status_code=201,
        summary="Create a user",
        response_model=SuccessEnvelope[UserResponse],
        responses=_CONFLICT,
    )
    async def create_user(req: CreateUserRequest):
        return await handler.create(req)

    @router.put(
        "/{user_id}",
        summary="Update a user",
        response_model=SuccessEnvelope[UserResponse],
        responses=_NOT_FOUND,
    )
    async def update_user(user_id: Annotated[int, Path(ge=1)], req: UpdateUserRequest):
        return await handler.update(user_id, req)

    @router.delete(
        "/{user_id}",
        summary="Delete a user",
        response_model=SuccessEnvelope,
        responses={**_NOT_FOUND, **_CONFLICT},
    )
    async def delete_user(user_id: Annotated[int, Path(ge=1)]):
        return await handler.delete(user_id)

    return router
