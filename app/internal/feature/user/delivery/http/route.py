"""User route definitions.

Mirrors the Go ``delivery/http/route.go``: given a fully-constructed handler,
build an :class:`APIRouter` and bind each path to a handler method. The router
is mounted onto the shared API group by the feature object in ``set.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.internal.auth.delivery.http.dependencies import AuthGuard
from app.internal.feature.user.delivery.http.dto.user import (
    CreateUserRequest,
    ListUsersQuery,
    UpdateUserRequest,
    UserListResponse,
    UserModuleStatusResponse,
    UserResponse,
)
from app.internal.feature.user.delivery.http.handler import UserHandler
from app.pkg.auth.permissions import Permission
from app.utils.openapi import ErrorEnvelope, SuccessEnvelope

# Shared error-envelope docs (documentation-only; handlers return JSONResponse).
_NOT_FOUND = {404: {"model": ErrorEnvelope, "description": "User not found"}}
_CONFLICT = {409: {"model": ErrorEnvelope, "description": "Conflicting state"}}
_UNAUTHORIZED = {401: {"model": ErrorEnvelope, "description": "Missing or invalid JWT"}}
_FORBIDDEN = {403: {"model": ErrorEnvelope, "description": "Insufficient permission"}}


def register_routes(handler: UserHandler, auth: AuthGuard) -> APIRouter:
    router = APIRouter(prefix="/users", tags=["users"])

    @router.get(
        "/status",
        summary="Public user module status (no auth)",
        description=(
            "**Example — no authentication.** Callable without an ``Authorization`` header. "
            "Contrast with ``GET /users`` which requires the ``user:read`` permission."
        ),
        response_model=SuccessEnvelope[UserModuleStatusResponse],
    )
    async def user_module_status():
        return await handler.status()

    @router.get(
        "",
        summary="List users (auth + permission)",
        description=(
            "**Protected.** Requires ``Authorization: Bearer <token>`` with permission ``user:read``."
        ),
        response_model=SuccessEnvelope[UserListResponse],
        responses={**_UNAUTHORIZED, **_FORBIDDEN},
        dependencies=[Depends(auth.require_permissions(Permission.USER_READ))],
    )
    async def list_users(query: Annotated[ListUsersQuery, Query()]):
        return await handler.list(query)

    @router.get(
        "/{user_id}",
        summary="Get a user by ID (auth + permission)",
        description="**Protected.** Requires JWT permission ``user:read``.",
        response_model=SuccessEnvelope[UserResponse],
        responses={**_NOT_FOUND, **_UNAUTHORIZED, **_FORBIDDEN},
        dependencies=[Depends(auth.require_permissions(Permission.USER_READ))],
    )
    async def get_user(user_id: Annotated[int, Path(ge=1)]):
        return await handler.get(user_id)

    @router.post(
        "",
        status_code=201,
        summary="Create a user (auth + permission)",
        description="**Protected.** Requires JWT permission ``user:create``.",
        response_model=SuccessEnvelope[UserResponse],
        responses={**_CONFLICT, **_UNAUTHORIZED, **_FORBIDDEN},
        dependencies=[Depends(auth.require_permissions(Permission.USER_CREATE))],
    )
    async def create_user(req: CreateUserRequest):
        return await handler.create(req)

    @router.put(
        "/{user_id}",
        summary="Update a user (auth + permission)",
        description="**Protected.** Requires JWT permission ``user:update``.",
        response_model=SuccessEnvelope[UserResponse],
        responses={**_NOT_FOUND, **_UNAUTHORIZED, **_FORBIDDEN},
        dependencies=[Depends(auth.require_permissions(Permission.USER_UPDATE))],
    )
    async def update_user(
        user_id: Annotated[int, Path(ge=1)],
        req: UpdateUserRequest,
    ):
        return await handler.update(user_id, req)

    @router.delete(
        "/{user_id}",
        summary="Delete a user (auth + permission)",
        description="**Protected.** Requires JWT permission ``user:delete``.",
        response_model=SuccessEnvelope,
        responses={**_NOT_FOUND, **_CONFLICT, **_UNAUTHORIZED, **_FORBIDDEN},
        dependencies=[Depends(auth.require_permissions(Permission.USER_DELETE))],
    )
    async def delete_user(user_id: Annotated[int, Path(ge=1)]):
        return await handler.delete(user_id)

    return router
