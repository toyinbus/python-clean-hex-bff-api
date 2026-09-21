"""Usecase unit tests.

Mirrors the Go testing philosophy: standard-library only, function-field mocks
for the ports (no third-party mocking framework), verifying business rules and
every error path. Async methods are driven with ``asyncio.run`` so no extra
test plugin is required.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest

from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
)
from app.internal.feature.user.domain.port.user import ListUsersFilter, UserRepository
from app.internal.feature.user.usecase.user_usecase import UserUsecaseImpl
from app.pkg import error_codes
from app.utils import apperror

TEST_DEFAULT_LIMIT = 20
TEST_MAX_LIMIT = 100


def _user(user_id: int = 1, status: str = "active", email: str = "a@example.com") -> User:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return User(id=user_id, name="Alice", email=email, status=status,
                created_at=now, updated_at=now)


class MockUserRepository(UserRepository):
    """Function-field mock — each test wires only the methods it needs."""

    def __init__(self) -> None:
        self.list_fn = None
        self.get_by_id_fn = None
        self.get_by_email_fn = None
        self.create_fn = None
        self.update_fn = None
        self.delete_fn = None

    async def list(self, filter: ListUsersFilter) -> ListUsersResult:
        return self.list_fn(filter) if self.list_fn else ListUsersResult()

    async def get_by_id(self, user_id: int) -> User:
        if self.get_by_id_fn:
            return self.get_by_id_fn(user_id)
        return _user(user_id)

    async def get_by_email(self, email: str):
        return self.get_by_email_fn(email) if self.get_by_email_fn else None

    async def create(self, params: CreateUserParams) -> User:
        return self.create_fn(params) if self.create_fn else _user(99, params.status, params.email)

    async def update(self, params: UpdateUserParams) -> User:
        return self.update_fn(params) if self.update_fn else _user(params.id)

    async def delete(self, user_id: int) -> None:
        if self.delete_fn:
            self.delete_fn(user_id)


def _new_usecase(repo: MockUserRepository) -> UserUsecaseImpl:
    return UserUsecaseImpl(repo, TEST_DEFAULT_LIMIT, TEST_MAX_LIMIT)


def test_create_success():
    repo = MockUserRepository()
    repo.get_by_email_fn = lambda email: None
    repo.create_fn = lambda p: _user(5, p.status, p.email)
    uc = _new_usecase(repo)

    result = asyncio.run(uc.create(CreateUserParams(name="Alice", email="new@example.com")))

    assert result.id == 5
    assert result.email == "new@example.com"


def test_create_requires_name():
    uc = _new_usecase(MockUserRepository())
    with pytest.raises(apperror.BadRequestError):
        asyncio.run(uc.create(CreateUserParams(name="", email="a@example.com")))


def test_create_rejects_invalid_email():
    uc = _new_usecase(MockUserRepository())
    with pytest.raises(apperror.BadRequestError):
        asyncio.run(uc.create(CreateUserParams(name="Alice", email="not-email")))


def test_create_rejects_duplicate_email():
    repo = MockUserRepository()
    repo.get_by_email_fn = lambda email: _user(1, email=email)
    uc = _new_usecase(repo)

    with pytest.raises(apperror.AlreadyExistsError) as exc:
        asyncio.run(uc.create(CreateUserParams(name="Alice", email="dup@example.com")))
    assert exc.value.code == error_codes.USER_EMAIL_TAKEN


def test_create_rejects_invalid_status():
    uc = _new_usecase(MockUserRepository())
    with pytest.raises(apperror.BadRequestError):
        asyncio.run(uc.create(CreateUserParams(name="A", email="a@example.com", status="nope")))


def test_get_propagates_not_found():
    repo = MockUserRepository()

    def boom(_):
        raise apperror.NotFoundError("user not found")

    repo.get_by_id_fn = boom
    uc = _new_usecase(repo)

    with pytest.raises(apperror.NotFoundError):
        asyncio.run(uc.get(42))


def test_update_rejects_duplicate_email_of_other_user():
    repo = MockUserRepository()
    repo.get_by_id_fn = lambda uid: _user(uid)
    repo.get_by_email_fn = lambda email: _user(2, email=email)  # different id
    uc = _new_usecase(repo)

    with pytest.raises(apperror.AlreadyExistsError):
        asyncio.run(uc.update(UpdateUserParams(id=1, email="taken@example.com")))


def test_update_allows_same_email_for_same_user():
    repo = MockUserRepository()
    repo.get_by_id_fn = lambda uid: _user(uid, email="same@example.com")
    repo.get_by_email_fn = lambda email: _user(1, email=email)  # same id
    repo.update_fn = lambda p: _user(p.id, email="same@example.com")
    uc = _new_usecase(repo)

    result = asyncio.run(uc.update(UpdateUserParams(id=1, email="same@example.com")))
    assert result.id == 1


def test_delete_active_user_conflicts():
    repo = MockUserRepository()
    repo.get_by_id_fn = lambda uid: _user(uid, status="active")
    uc = _new_usecase(repo)

    with pytest.raises(apperror.ConflictError):
        asyncio.run(uc.delete(1))


def test_delete_inactive_user_succeeds():
    repo = MockUserRepository()
    repo.get_by_id_fn = lambda uid: _user(uid, status="inactive")
    deleted: list[int] = []
    repo.delete_fn = deleted.append
    uc = _new_usecase(repo)

    asyncio.run(uc.delete(1))
    assert deleted == [1]
