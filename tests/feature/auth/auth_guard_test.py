"""AuthGuard and JWT validator unit tests."""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.internal.feature.auth.delivery.http.dependencies import AuthGuard
from app.internal.feature.auth.infra.service.jwt_token_validator import JwtTokenValidatorImpl
from app.pkg.auth.permissions import Permission
from app.utils import apperror


def _validator() -> JwtTokenValidatorImpl:
    return JwtTokenValidatorImpl(
        secret="test-secret",
        algorithm="HS256",
        default_expire_minutes=60,
    )


def _token(*permissions: Permission) -> str:
    return _validator().issue(
        subject="42",
        permissions=frozenset(permissions),
    )


def _client(auth: AuthGuard) -> TestClient:
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(auth.require_permissions(Permission.USER_READ))])
    async def protected():
        return {"ok": True}

    @app.exception_handler(apperror.AppError)
    async def _app_error(_, exc: apperror.AppError):
        from app.utils.response import response_error

        return response_error(http_code=exc.http_status, code=exc.code, message=exc.message)

    return TestClient(app, raise_server_exceptions=False)


def test_missing_token_returns_401():
    auth = AuthGuard(_validator(), auth_enabled=True)
    resp = _client(auth).get("/protected")
    assert resp.status_code == 401
    assert resp.json()["code"] == "20001"


def test_invalid_token_returns_401():
    auth = AuthGuard(_validator(), auth_enabled=True)
    resp = _client(auth).get("/protected", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401
    assert resp.json()["code"] == "20002"


def test_wrong_permission_returns_403():
    auth = AuthGuard(_validator(), auth_enabled=True)
    token = _token(Permission.USER_CREATE)
    resp = _client(auth).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
    assert resp.json()["code"] == "20004"


def test_correct_permission_allows_access():
    auth = AuthGuard(_validator(), auth_enabled=True)
    token = _token(Permission.USER_READ)
    resp = _client(auth).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_auth_disabled_skips_checks():
    auth = AuthGuard(_validator(), auth_enabled=False)
    resp = _client(auth).get("/protected")
    assert resp.status_code == 200
