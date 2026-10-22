import pytest

from app.core.config import Settings, _validate_production_settings


def test_redis_url_uses_configured_password():
    settings = Settings(_env_file=None, REDIS_HOST="redis", REDIS_PASSWORD="secret")

    assert settings.REDIS_URL == "redis://:secret@redis:6379/0"


def test_production_requires_redis_password():
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="production-secret",
        SMTP_HOST="smtp.example.test",
        SMTP_TLS_MODE="starttls",
    )

    with pytest.raises(RuntimeError, match="REDIS_PASSWORD must be set in production"):
        _validate_production_settings(settings)
