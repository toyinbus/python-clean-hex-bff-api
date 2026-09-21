"""User usecase — Application Business layer.

Orchestrates business rules and delegates persistence to the repository port.
It NEVER imports infrastructure (no repository implementation, no db model) and
NEVER touches config directly — the limit primitives are injected via the
constructor by ``set.py``. It MAY import ``app.pkg.error_codes`` (pure domain-code
constants) to tag domain-specific outcomes.
"""

from __future__ import annotations

from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
    ensure_valid_email,
)
from app.internal.feature.user.domain.port.user import (
    ListUsersFilter,
    UserRepository,
    UserStatus,
    UserUsecase,
)
from app.pkg import error_codes
from app.utils import apperror


class UserUsecaseImpl(UserUsecase):
    def __init__(self, repo: UserRepository, default_limit: int, max_limit: int) -> None:
        self._repo = repo
        self._default_limit = default_limit
        self._max_limit = max_limit

    async def list(self, filter: ListUsersFilter) -> ListUsersResult:
        return await self._repo.list(filter)

    async def get(self, user_id: int) -> User:
        # Repository raises NotFoundError when missing; usecase just propagates.
        return await self._repo.get_by_id(user_id)

    async def create(self, params: CreateUserParams) -> User:
        # Format validation that needs no external data can live in the entity;
        # business validation that needs a lookup lives here.
        if not params.name:
            raise apperror.BadRequestError("name is required")
        ensure_valid_email(params.email)
        self._validate_status(params.status)

        existing = await self._repo.get_by_email(params.email)
        if existing is not None:
            raise apperror.AlreadyExistsError(
                "email already registered", code=error_codes.USER_EMAIL_TAKEN
            )

        return await self._repo.create(params)

    async def update(self, params: UpdateUserParams) -> User:
        # Ensure the target exists first (raises NotFoundError otherwise).
        await self._repo.get_by_id(params.id)

        if params.email is not None:
            ensure_valid_email(params.email)
            other = await self._repo.get_by_email(params.email)
            if other is not None and other.id != params.id:
                raise apperror.AlreadyExistsError(
                    "email already registered", code=error_codes.USER_EMAIL_TAKEN
                )
        if params.status is not None:
            self._validate_status(params.status)

        return await self._repo.update(params)

    async def delete(self, user_id: int) -> None:
        existing = await self._repo.get_by_id(user_id)
        # Business rule enforced on the entity itself.
        if not existing.can_be_deleted():
            raise apperror.ConflictError("cannot delete an active user")
        await self._repo.delete(user_id)

    @staticmethod
    def _validate_status(status: str) -> None:
        if status not in (s.value for s in UserStatus):
            raise apperror.BadRequestError(f"invalid status: {status}")
