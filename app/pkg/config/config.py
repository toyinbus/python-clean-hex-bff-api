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

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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


@lru_cache
def provide_config() -> Config:
    """Load configuration once (cached). Equivalent to Go `config.ProvideConfig`."""
    return Config()
