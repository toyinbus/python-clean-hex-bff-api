"""Application configuration.

Mirrors the Go `pkg/config` package. Every tunable value lives here in exactly
one place and is loaded from environment variables (with sane defaults) using
``pydantic-settings`` — the FastAPI-idiomatic equivalent of the Go Config
struct with ``env`` + ``default`` tags.

Rules (see ARCHITECTURE.md § Configuration Strategy):
  * Secrets / infrastructure addresses -> env only.
  * Tunable-per-environment values -> env with a default here.
  * Fixed business constants -> a ``constants`` module or ``domain/port``.

No feature code imports this module. Config values are extracted as
primitives at the DI boundary (``app/di/container.py`` + each feature
``set.py``) and injected into constructors.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Committed default — must be overridden in production when AUTH_ENABLED=true.
DEFAULT_JWT_SECRET = "change-me-in-production"
JWT_SECRET_MIN_LENGTH = 32
_PRODUCTION_ENVIRONMENTS = frozenset({"production", "prod"})


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Application ───────────────────────────────────────────────────────────
    APP_NAME: str = "python-clean-hex-bff-api"
    ENVIRONMENT: str = "development"
    API_BASE_PATH: str = "/api/v1"
    ENABLE_DOCS: bool = True

    # ── Logging ─────────────────────────────────────────────────────────────
    # LOG_FORMAT: "console" -> human-readable one-liner (local development)
    #             "json"    -> one JSON object per line, ready for CloudWatch /
    #                          Elastic / Loki with no extra parser (production).
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "console"
    # LOG_BODIES: log request/response bodies for inspection. OFF by default —
    # it is a debugging aid (bodies may contain PII). When on, values are passed
    # through the redactor and truncated to LOG_BODY_MAX_BYTES.
    LOG_BODIES: bool = False
    LOG_BODY_MAX_BYTES: int = 2048
    # LOG_REDACT: mask sensitive fields in logged bodies. ON by default (secure).
    # Set to false ONLY on a trusted local machine to inspect raw values while
    # debugging — never on a deployed/shared server.
    LOG_REDACT: bool = True

    # ── REST server ───────────────────────────────────────────────────────────
    REST_API_HOST: str = "0.0.0.0"
    REST_API_PORT: int = 8080

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    # ── Storage type ──────────────────────────────────────────────────────────
    # Explicit switch (never inferred from whether DB_* is filled):
    #   "memory"   -> mocked in-memory repo; no DB connection, nothing to check.
    #   "postgres" -> real asyncpg repo; the pool is opened AND pinged at startup,
    #                 so an unreachable/misconfigured DB makes the app fail fast
    #                 (it will NOT start) instead of silently degrading.
    STORAGE_TYPE: str = "memory"

    # ── Secrets / infrastructure (env only) ───────────────────────────────────
    # Used only when STORAGE_TYPE=postgres. With the default "memory" backend
    # these are ignored, so the demo runs with zero external infrastructure.
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_NAME: str = "app_db_dev"
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 10
    DB_CONNECT_TIMEOUT_SEC: int = 5

    # ── JWT / auth ────────────────────────────────────────────────────────────
    # When AUTH_ENABLED=false every route skips token checks (local dev / tests).
    AUTH_ENABLED: bool = True
    JWT_SECRET: str = DEFAULT_JWT_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    # Dev-only endpoint POST /api/v1/auth/token to mint test JWTs (Swagger-friendly).
    AUTH_DEV_TOKEN_ENABLED: bool = True


def validate_auth_settings(cfg: Config) -> None:
    """Fail-fast on unsafe JWT settings. Call from the composition root at startup.

    When ``AUTH_ENABLED=false`` (tests / local bypass) this is a no-op.
    In production it refuses to start with the committed default secret, an empty
    secret, or a secret that is too short.
    """
    if not cfg.AUTH_ENABLED:
        return

    secret = cfg.JWT_SECRET.strip()
    if not secret:
        raise RuntimeError("JWT_SECRET must not be empty when AUTH_ENABLED=true")

    is_production = cfg.ENVIRONMENT.strip().lower() in _PRODUCTION_ENVIRONMENTS
    if is_production:
        if secret == DEFAULT_JWT_SECRET:
            raise RuntimeError(
                "JWT_SECRET is still the default placeholder — set a strong secret in production"
            )
        if len(secret) < JWT_SECRET_MIN_LENGTH:
            raise RuntimeError(
                f"JWT_SECRET must be at least {JWT_SECRET_MIN_LENGTH} characters in production"
            )
        if cfg.AUTH_DEV_TOKEN_ENABLED:
            raise RuntimeError(
                "AUTH_DEV_TOKEN_ENABLED must be false in production "
                "(POST /auth/token must not mint tokens in prod)"
            )
        return

    if secret == DEFAULT_JWT_SECRET:
        logger.warning(
            "JWT_SECRET is still the default placeholder. "
            "Set a strong secret before deploying (ENVIRONMENT=production)."
        )


@lru_cache
def provide_config() -> Config:
    """Load configuration once (cached). Equivalent to Go `config.ProvideConfig`."""
    return Config()
