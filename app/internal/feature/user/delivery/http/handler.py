"""User HTTP handler (Interface Adapters — primary/driving side).

Thin controllers: bind/extract the request, call the usecase port, and shape
the response envelope. The handler imports ``dto``, ``port`` and ``utils`` —
never the repository directly (it uses the DTO ``from_entity`` factories for
entity -> response conversion).

Domain errors raised by the usecase are ``AppError`` subclasses that already
carry their HTTP status and 5-digit code, so a single mapping turns any of them
into the standard error envelope; anything unexpected falls back to 500.
"""

from __future__ import annotations

from http import HTTPStatus

from fastapi.responses import JSONResponse

from app.internal.feature.user.delivery.http.dto.user import (
    CreateUserRequest,
    ListUsersQuery,
    UpdateUserRequest,
    UserListResponse,
    user_response_from_entity,
    user_responses_from_entities,
)
from app.internal.feature.user.domain.entity.user import CreateUserParams, UpdateUserParams
from app.internal.feature.user.domain.port.user import UserUsecase
from app.utils import apperror
from app.utils.response import response_error, response_success


class UserHandler:
    def __init__(self, usecase: UserUsecase) -> None:
        self._uc = usecase

    async def list(self, query: ListUsersQuery) -> JSONResponse:
        filter = query.to_filter()
        try:
            result = await self._uc.list(filter)
        except Exception as err:
            return _map_error(err, "failed to list users")

        norm = filter.query.normalize()
        payload = UserListResponse(
            items=user_responses_from_entities(result.items),
            total=result.total,
            limit=norm.limit,
            offset=norm.offset,
        )
        return response_success(payload.model_dump(mode="json"))

    async def get(self, user_id: int) -> JSONResponse:
        try:
            user = await self._uc.get(user_id)
        except Exception as err:
            return _map_error(err, "failed to get user")
        return response_success(user_response_from_entity(user).model_dump(mode="json"))

    async def create(self, req: CreateUserRequest) -> JSONResponse:
        try:
            user = await self._uc.create(
                CreateUserParams(name=req.name, email=str(req.email), status=req.status.value)
            )
        except Exception as err:
            return _map_error(err, "failed to create user")
        return response_success(
            user_response_from_entity(user).model_dump(mode="json"),
            http_code=HTTPStatus.CREATED,
        )

    async def update(self, user_id: int, req: UpdateUserRequest) -> JSONResponse:
        try:
            user = await self._uc.update(
                UpdateUserParams(
                    id=user_id,
                    name=req.name,
                    email=None if req.email is None else str(req.email),
                    status=None if req.status is None else req.status.value,
                )
            )
        except Exception as err:
            return _map_error(err, "failed to update user")
        return response_success(user_response_from_entity(user).model_dump(mode="json"))

    async def delete(self, user_id: int) -> JSONResponse:
        try:
            await self._uc.delete(user_id)
        except Exception as err:
            return _map_error(err, "failed to delete user")
        return response_success({"message": "user deleted"})


def _map_error(err: Exception, fallback_message: str) -> JSONResponse:
    """Map a raised error onto the standard error envelope."""
    if isinstance(err, apperror.AppError):
        return response_error(
            http_code=err.http_status,
            code=err.code,
            message=err.message,
            err=err,
        )
    return response_error(
        http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        message=fallback_message,
        err=err,
    )
