"""Composition root — the single place that wires the whole object graph.

Mirrors the Go ``di/set.go`` + generated ``wire_gen.go``. Using
``dependency-injector`` gives an explicit, declarative container: shared infra
(config, and in a real service the DB/Redis clients) lives here, each feature's
own container is mounted as a sub-container, and ``features`` collects every
feature's route registrar — the equivalent of Go's ``ProvideFeatures`` returning
``[]server.HTTPRouteRegistrar``.

Import rule (matching Go): this module references only each feature's ``set.py``
(feature root) — never its inner ``usecase``/``infra``/``port`` packages.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from app.internal.auth.set import AuthContainer
from app.internal.feature.user.set import UserContainer
from app.pkg.config.config import Config
from app.pkg.database import Database


class ApplicationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    # ── Shared infrastructure ────────────────────────────────────────────────
    # App-wide async DB pool holder. Cheap to construct (no connection yet); the
    # pool is opened + health-checked at startup only when STORAGE_TYPE=postgres
    # (see app.main lifespan). Injected into feature repositories that need it.
    database = providers.Singleton(Database)

    # ── Auth (shared JWT guard + helper routes) ───────────────────────────────
    auth = providers.Container(AuthContainer, config=config)

    # ── Features ──────────────────────────────────────────────────────────────
    user = providers.Container(
        UserContainer,
        config=config,
        database=database,
        auth_guard=auth.auth_guard,
    )

    # Collected route registrars, consumed by app.main when mounting routes.
    features = providers.List(
        auth.feature,
        user.feature,
    )


def build_container(cfg: Config) -> ApplicationContainer:
    """Instantiate the container and load configuration primitives into it."""
    container = ApplicationContainer()
    container.config.from_dict(cfg.model_dump())
    return container
