"""Auth example route tests — public vs protected endpoints."""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.internal.feature.auth.delivery.http.dependencies import AuthGuard
from app.internal.feature.auth.delivery.http.handler import AuthHandler
from app.internal.feature.auth.delivery.http.route import register_routes
from app.internal.feature.auth.infra.service.jwt_token_validator import JwtTokenValidatorImpl
from app.pkg.auth.permissions import Permission
from app.utils import apperror


def _validator() -> JwtTokenValidatorImpl:
    return JwtTokenValidatorImpl(
        secret="test-secret",
        algorithm="HS256",
        default_expire_minutes=60,
    )


def _client(*, auth_enabled: bool = True) -> TestClient:
    validator = _validator()
    auth = AuthGuard(validator, auth_enabled=auth_enabled)
    handler = AuthHandler(validator, default_expire_minutes=60)
    app = FastAPI()
    api = APIRouter(prefix="/api/v1")
    api.include_router(register_routes(handler, auth, dev_token_enabled=True))
    app.include_router(api)

    @app.exception_handler(apperror.AppError)
    async def _app_error(_, exc: apperror.AppError):
        from app.utils.response import response_error

        return response_error(http_code=exc.http_status, code=exc.code, message=exc.message)

    return TestClient(app, raise_server_exceptions=False)


def test_public_route_works_without_token():
    resp = _client().get("/api/v1/auth/public")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["auth_required"] is False


def test_me_route_requires_token():
    resp = _client().get("/api/v1/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "20001"


def test_me_route_returns_caller_from_token():
    token = _validator().issue(subject="99", permissions=frozenset({Permission.USER_READ}))
    resp = _client().get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["user_id"] == "99"
    assert resp.json()["data"]["permissions"] == ["user:read"]


def test_permissions_route_is_public():
    resp = _client().get("/api/v1/auth/permissions")
    assert resp.status_code == 200
    assert "user:read" in resp.json()["data"]
