"""Application entrypoint.

Mirrors the Go ``cmd/main.go`` + ``di.ProvideHttpServer``:
  1. load config,
  2. build the DI container (composition root),
  3. create the FastAPI app + middleware + health check,
  4. mount every feature's routes under the API base path,
  5. install exception handlers so ALL responses use the standard envelope.

Run locally with:  ``uvicorn app.main:app --reload``  (or ``python -m app.main``).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.di.container import ApplicationContainer, build_container
from app.internal.middleware.access_log import AccessLogMiddleware
from app.internal.middleware.body_log import BodyLogMiddleware
from app.internal.middleware.request_context import RequestContextMiddleware
from app.pkg import sensitive_keys
from app.pkg.config.config import Config, provide_config, validate_auth_settings
from app.utils import apperror
from app.utils.logging_config import configure_logging
from app.utils.response import response_error


def _build_lifespan(cfg: Config, container: ApplicationContainer):
    """Startup/shutdown hook.

    For ``STORAGE_TYPE=postgres`` it opens the pool and pings it — if the DB is
    unreachable or misconfigured the exception propagates and the app fails to
    start (fail-fast). For ``memory`` it is a no-op, so the demo needs no DB.
    """

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if cfg.STORAGE_TYPE == "postgres":
            await container.database().connect(
                host=cfg.DB_HOST,
                port=cfg.DB_PORT,
                user=cfg.DB_USER,
                password=cfg.DB_PASSWORD,
                database=cfg.DB_NAME,
                min_size=cfg.DB_POOL_MIN,
                max_size=cfg.DB_POOL_MAX,
                timeout=cfg.DB_CONNECT_TIMEOUT_SEC,
            )
        yield
        if cfg.STORAGE_TYPE == "postgres":
            await container.database().disconnect()

    return lifespan


def create_app() -> FastAPI:
    cfg = provide_config()
    configure_logging(cfg.LOG_LEVEL, cfg.LOG_FORMAT)
    validate_auth_settings(cfg)
    # We emit our own structured access log (AccessLogMiddleware); silence
    # uvicorn's default access logger so lines are not duplicated.
    logging.getLogger("uvicorn.access").disabled = True
    container = build_container(cfg)

    app = FastAPI(
        title="Python CleanHex BFF API",
        version="1.0.0",
        description="Demo BFF (Backend-for-Frontend) built with FastAPI CleanHex architecture.",
        docs_url="/docs" if cfg.ENABLE_DOCS else None,
        redoc_url="/redoc" if cfg.ENABLE_DOCS else None,
        openapi_url="/openapi.json" if cfg.ENABLE_DOCS else None,
        lifespan=_build_lifespan(cfg, container),
    )
    app.state.container = container

    # Middleware order: add inner first, outer last. RequestContextMiddleware
    # must be OUTERMOST so the request-id ContextVar is set before the inner
    # layers (access log, body log) read it.
    if cfg.LOG_BODIES:
        if not cfg.LOG_REDACT:
            logging.getLogger("app").warning(
                "LOG_REDACT=false: request/response bodies are logged UNMASKED. "
                "Use only on a trusted local machine, never on a deployed server."
            )
        app.add_middleware(  # innermost — sees the final request/response bodies
            BodyLogMiddleware,
            max_bytes=cfg.LOG_BODY_MAX_BYTES,
            extra_keys=sensitive_keys.SENSITIVE_KEYS,
            partial_keys=sensitive_keys.PARTIAL_KEYS,
            redact_enabled=cfg.LOG_REDACT,
        )
    app.add_middleware(AccessLogMiddleware)  # inner
    app.add_middleware(RequestContextMiddleware)  # outer

    _register_exception_handlers(app)

    @app.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok"}

    # Mount every feature's routes under the API base path — the Python
    # equivalent of Go's `for _, f := range features { f.RegisterHTTP(api) }`.
    api = APIRouter(prefix=cfg.API_BASE_PATH)
    for feature in container.features():
        feature.register_http(api)
    app.include_router(api)

    _configure_openapi_security(app)

    return app


def _configure_openapi_security(app: FastAPI) -> None:
    """Document Bearer JWT auth in Swagger when docs are enabled."""

    if app.openapi_url is None:
        return

    original_openapi = app.openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = original_openapi()
        schema.setdefault("components", {}).setdefault("securitySchemes", {})[
            "BearerAuth"
        ] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "JWT access token. Permissions are carried in the ``permissions`` claim "
                "(see GET /auth/permissions). Mint a dev token via POST /auth/token when "
                "AUTH_DEV_TOKEN_ENABLED=true."
            ),
        }
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(apperror.AppError)
    async def _app_error_handler(_: Request, exc: apperror.AppError):
        return response_error(
            http_code=exc.http_status, code=exc.code, message=exc.message, err=exc
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(_: Request, exc: RequestValidationError):
        # pydantic errors embed the raw `input` value (and a docs `url`); never
        # echo those back — a bad `password`/`token` field would leak verbatim.
        # Keep only the safe fields the frontend needs to localize the error.
        safe_errors = [
            {k: v for k, v in e.items() if k in ("loc", "msg", "type")}
            for e in exc.errors()
        ]
        return response_error(
            http_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            code=apperror.CODE_INVALID_INPUT,
            message="invalid request",
            data={"errors": safe_errors},
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception):
        return response_error(
            http_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code=apperror.CODE_INTERNAL,
            message="internal server error",
            err=exc,
        )


app = create_app()


def main() -> None:
    import uvicorn

    cfg = provide_config()
    # log_config=None -> keep the config installed by create_app (don't let
    # uvicorn reset logging to its own text format).
    uvicorn.run(
        "app.main:app",
        host=cfg.REST_API_HOST,
        port=cfg.REST_API_PORT,
        reload=False,
        log_config=None,
    )


if __name__ == "__main__":
    main()
