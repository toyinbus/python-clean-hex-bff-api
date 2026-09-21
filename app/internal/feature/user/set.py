"""User feature wiring.

Mirrors the Go ``feature/user/set.go``:
  * ``UserFeature``  ~ the ``Feature`` struct that implements the route
    registrar contract (``server.HTTPRouteRegistrar``).
  * ``UserContainer`` ~ the ``FeatureSet`` wire set. Each ``providers.*`` entry
    that constructs an ``*Impl`` and feeds it into a constructor expecting the
    matching port is the DI equivalent of ``wire.Bind(port, impl)``.

Config primitives are extracted here (the ``ProvideXxx`` wrapper equivalent) so
no inner layer ever imports ``pkg/config``.
"""

from __future__ import annotations

from dependency_injector import containers, providers
from fastapi import APIRouter

from app.internal.feature.user.delivery.http.handler import UserHandler
from app.internal.feature.user.delivery.http.route import register_routes
from app.internal.feature.user.infra.db.user_repository import UserRepositoryImpl
from app.internal.feature.user.infra.db.user_repository_postgres import (
    UserRepositoryPostgres,
)
from app.internal.feature.user.usecase.user_usecase import UserUsecaseImpl


class UserFeature:
    """Holds the handler and mounts the feature's routes (route registrar)."""

    def __init__(self, handler: UserHandler) -> None:
        self._handler = handler

    def register_http(self, api: APIRouter) -> None:
        api.include_router(register_routes(self._handler))


class UserContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    database = providers.Dependency()  # shared pool holder (from the app container)

    # Repository (driven adapter) -> satisfies port.UserRepository.
    # The concrete adapter is chosen by STORAGE_TYPE at wiring time; both
    # implement the same port, so no inner layer changes when switching.
    user_repository = providers.Selector(
        config.STORAGE_TYPE,
        memory=providers.Singleton(UserRepositoryImpl),
        postgres=providers.Singleton(UserRepositoryPostgres, db=database),
    )

    # Usecase -> satisfies port.UserUsecase. Config extracted to primitives here.
    user_usecase = providers.Singleton(
        UserUsecaseImpl,
        repo=user_repository,
        default_limit=config.DEFAULT_PAGE_SIZE,
        max_limit=config.MAX_PAGE_SIZE,
    )

    # Handler (driving adapter).
    handler = providers.Singleton(UserHandler, usecase=user_usecase)

    # Feature aggregate (route registrar).
    feature = providers.Singleton(UserFeature, handler=handler)
