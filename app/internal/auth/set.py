"""Auth wiring — JWT validator, route guard, optional dev token routes."""

from __future__ import annotations

from dependency_injector import containers, providers
from fastapi import APIRouter

from app.internal.auth.delivery.http.dependencies import AuthGuard
from app.internal.auth.delivery.http.handler import AuthHandler
from app.internal.auth.delivery.http.route import register_routes
from app.internal.auth.infra.service.jwt_token_validator import JwtTokenValidatorImpl


class AuthFeature:
    """Mounts auth helper routes (permission catalog, optional dev token)."""

    def __init__(
        self,
        handler: AuthHandler,
        auth: AuthGuard,
        *,
        dev_token_enabled: bool,
    ) -> None:
        self._handler = handler
        self._auth = auth
        self._dev_token_enabled = dev_token_enabled

    def register_http(self, api: APIRouter) -> None:
        api.include_router(
            register_routes(
                self._handler,
                self._auth,
                dev_token_enabled=self._dev_token_enabled,
            )
        )


class AuthContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    token_validator = providers.Singleton(
        JwtTokenValidatorImpl,
        secret=config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
        default_expire_minutes=config.JWT_EXPIRE_MINUTES,
    )

    auth_guard = providers.Singleton(
        AuthGuard,
        validator=token_validator,
        auth_enabled=config.AUTH_ENABLED,
    )

    handler = providers.Singleton(
        AuthHandler,
        validator=token_validator,
        default_expire_minutes=config.JWT_EXPIRE_MINUTES,
    )

    feature = providers.Singleton(
        AuthFeature,
        handler=handler,
        auth=auth_guard,
        dev_token_enabled=config.AUTH_DEV_TOKEN_ENABLED,
    )
