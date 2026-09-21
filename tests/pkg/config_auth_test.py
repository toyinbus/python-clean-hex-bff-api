"""Auth-related config validation tests."""

from __future__ import annotations

import pytest

from app.pkg.config.config import Config, DEFAULT_JWT_SECRET, validate_auth_settings


def test_skips_when_auth_disabled():
    cfg = Config(AUTH_ENABLED=False, JWT_SECRET="")
    validate_auth_settings(cfg)  # no raise


def test_production_rejects_default_secret():
    cfg = Config(
        ENVIRONMENT="production",
        AUTH_ENABLED=True,
        JWT_SECRET=DEFAULT_JWT_SECRET,
        AUTH_DEV_TOKEN_ENABLED=False,
    )
    with pytest.raises(RuntimeError, match="default placeholder"):
        validate_auth_settings(cfg)


def test_production_rejects_short_secret():
    cfg = Config(
        ENVIRONMENT="production",
        AUTH_ENABLED=True,
        JWT_SECRET="too-short",
        AUTH_DEV_TOKEN_ENABLED=False,
    )
    with pytest.raises(RuntimeError, match="at least 32"):
        validate_auth_settings(cfg)


def test_production_rejects_dev_token_endpoint():
    cfg = Config(
        ENVIRONMENT="production",
        AUTH_ENABLED=True,
        JWT_SECRET="x" * 32,
        AUTH_DEV_TOKEN_ENABLED=True,
    )
    with pytest.raises(RuntimeError, match="AUTH_DEV_TOKEN_ENABLED"):
        validate_auth_settings(cfg)


def test_production_accepts_strong_secret():
    cfg = Config(
        ENVIRONMENT="production",
        AUTH_ENABLED=True,
        JWT_SECRET="x" * 32,
        AUTH_DEV_TOKEN_ENABLED=False,
    )
    validate_auth_settings(cfg)


def test_development_allows_default_secret():
    cfg = Config(
        ENVIRONMENT="development",
        AUTH_ENABLED=True,
        JWT_SECRET=DEFAULT_JWT_SECRET,
    )
    validate_auth_settings(cfg)
