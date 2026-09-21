"""Handler unit tests.

The handler is exercised through a minimal FastAPI app that mounts only the
user routes wired to a mocked usecase — verifying HTTP status codes, the
response envelope, and error mapping (the usecase itself is not under test here).
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.internal.feature.user.delivery.http.handler import UserHandler
from app.internal.feature.user.delivery.http.route import register_routes
from app.internal.feature.user.domain.entity.user import (
    CreateUserParams,
    ListUsersResult,
    UpdateUserParams,
    User,
)
from app.internal.feature.user.domain.port.user import ListUsersFilter, UserUsecase
from app.utils import apperror


def _user(user_id: int = 1) -> User:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return User(id=user_id, name="Alice", email="a@example.com", status="active",
                created_at=now, updated_at=now)


class MockUserUsecase(UserUsecase):
    def __init__(self) -> None:
        self.list_fn = None
        self.get_fn = None
        self.create_fn = None
        self.update_fn = None
        self.delete_fn = None

    async def list(self, filter: ListUsersFilter) -> ListUsersResult:
        return self.list_fn(filter) if self.list_fn else ListUsersResult(items=[_user()], total=1)

    async def get(self, user_id: int) -> User:
        return self.get_fn(user_id) if self.get_fn else _user(user_id)

    async def create(self, params: CreateUserParams) -> User:
        return self.create_fn(params) if self.create_fn else _user(7)

    async def update(self, params: UpdateUserParams) -> User:
        return self.update_fn(params) if self.update_fn else _user(params.id)

    async def delete(self, user_id: int) -> None:
        if self.delete_fn:
            self.delete_fn(user_id)


def _client(uc: MockUserUsecase) -> TestClient:
    app = FastAPI()
    api = APIRouter(prefix="/api/v1")
    api.include_router(register_routes(UserHandler(uc)))
    app.include_router(api)
    return TestClient(app, raise_server_exceptions=False)


def test_list_returns_envelope():
    c = _client(MockUserUsecase())
    resp = c.get("/api/v1/users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["code"] == apperror.CODE_OK
    assert body["data"]["total"] == 1


def test_get_success():
    c = _client(MockUserUsecase())
    resp = c.get("/api/v1/users/3")
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == 3


def test_get_not_found_maps_to_404():
    uc = MockUserUsecase()

    def boom(_):
        raise apperror.NotFoundError("user not found")

    uc.get_fn = boom
    resp = _client(uc).get("/api/v1/users/999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert body["code"] == apperror.CODE_NOT_FOUND


def test_create_returns_201():
    c = _client(MockUserUsecase())
    resp = c.post("/api/v1/users", json={"name": "Alice", "email": "a@example.com"})
    assert resp.status_code == 201
    assert resp.json()["data"]["id"] == 7


def test_create_validation_error_returns_422():
    c = _client(MockUserUsecase())
    resp = c.post("/api/v1/users", json={"name": "Alice", "email": "not-an-email"})
    assert resp.status_code == 422


def test_delete_conflict_maps_to_409():
    uc = MockUserUsecase()

    def boom(_):
        raise apperror.ConflictError("cannot delete an active user")

    uc.delete_fn = boom
    resp = _client(uc).delete("/api/v1/users/1")
    assert resp.status_code == 409
    assert resp.json()["code"] == apperror.CODE_CONFLICT
