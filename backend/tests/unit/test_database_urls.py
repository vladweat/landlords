import pytest
from app.core.config import Settings


def test_runtime_and_migration_database_urls_use_separate_credentials() -> None:
    config = Settings(
        _env_file=None,
        DB_HOST="postgres",
        DB_PORT=5432,
        DB_USER="landlords_runtime",
        DB_PASSWORD="runtime-secret",
        DB_NAME="landlords_db",
        MIGRATION_DB_USER="landlords_owner",
        MIGRATION_DB_PASSWORD="owner-secret",
    )

    assert config.DATABASE_URL == (
        "postgresql+psycopg2://landlords_runtime:runtime-secret"
        "@postgres:5432/landlords_db"
    )
    assert config.MIGRATION_DATABASE_URL == (
        "postgresql+psycopg2://landlords_owner:owner-secret"
        "@postgres:5432/landlords_db"
    )


def test_production_requires_distinct_migration_credentials() -> None:
    config = Settings(
        _env_file=None,
        APP_ENV="production",
        DB_USER="landlords_runtime",
        DB_PASSWORD="runtime-secret",
        MIGRATION_DB_USER=None,
        MIGRATION_DB_PASSWORD=None,
    )

    with pytest.raises(RuntimeError, match="MIGRATION_DB_USER"):
        _ = config.MIGRATION_DATABASE_URL


def test_partial_migration_credentials_are_rejected() -> None:
    config = Settings(
        _env_file=None,
        MIGRATION_DB_USER="landlords_owner",
        MIGRATION_DB_PASSWORD=None,
    )

    with pytest.raises(RuntimeError, match="must be set together"):
        _ = config.MIGRATION_DATABASE_URL
