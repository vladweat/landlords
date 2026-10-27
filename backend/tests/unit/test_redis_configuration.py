import pytest

from app.core.config import Settings, _validate_production_settings


def test_redis_url_reads_password_file_and_escapes_credentials(tmp_path):
    password_file = tmp_path / "redis.password"
    password_file.write_text("p@ss:word/with space\n", encoding="utf-8")
    settings = Settings(
        _env_file=None,
        REDIS_HOST="redis",
        REDIS_USERNAME="landlords api",
        REDIS_PASSWORD_FILE=str(password_file),
    )

    assert (
        settings.REDIS_URL
        == "redis://landlords%20api:p%40ss%3Aword%2Fwith%20space@redis:6379/0"
    )


def test_redis_url_keeps_local_legacy_password_compatibility():
    settings = Settings(_env_file=None, REDIS_HOST="redis", REDIS_PASSWORD="dev-secret")

    assert settings.REDIS_URL == "redis://:dev-secret@redis:6379/0"


def test_redis_password_file_error_does_not_reveal_path_or_content(tmp_path):
    missing_file = tmp_path / "private-secret-file"
    settings = Settings(
        _env_file=None,
        REDIS_USERNAME="landlords_api",
        REDIS_PASSWORD_FILE=str(missing_file),
    )

    with pytest.raises(RuntimeError, match="Unable to read Redis password file") as exc:
        _ = settings.REDIS_URL

    assert str(missing_file) not in str(exc.value)


def test_production_requires_redis_acl_identity_and_password_file():
    settings = Settings(
        _env_file=None,
        APP_ENV="production",
        SECRET_KEY="production-secret",
        SMTP_HOST="smtp.example.test",
        SMTP_TLS_MODE="starttls",
    )

    with pytest.raises(RuntimeError, match="REDIS_USERNAME must be set in production"):
        _validate_production_settings(settings)
