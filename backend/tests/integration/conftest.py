"""Фикстуры для интеграционных тестов внутри Docker-контейнера."""

from pathlib import Path
from unittest.mock import patch

import pytest
from alembic import command
from alembic.config import Config
from app.core.config import settings
from app.db.session import get_db_session
from app.main import create_app
from app.scripts.provision_runtime_db_role import provision_runtime_role
from app.services.email_service import EmailService
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

TEST_DB_NAME = "landlords_test"
ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def property_payload(
    *,
    city: str = "Москва",
    street: str = "Тестовая",
    house: str = "1",
    property_type: str = "apartment",
    size_m2: float = 50.0,
    **extra,
) -> dict:
    """Собрать тело запроса для создания объекта недвижимости."""
    payload = {
        "city": city,
        "street": street,
        "house": house,
        "type": property_type,
        "size_m2": size_m2,
    }
    payload.update(extra)
    return payload


@pytest.fixture(scope="session")
def test_engine():
    """Создать отдельную test DB, применить миграции owner role и вернуть runtime engine."""
    admin_url = make_url(settings.MIGRATION_DATABASE_URL).set(database="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin_engine.dispose()

    provision_runtime_role(TEST_DB_NAME)
    migration_url = make_url(settings.MIGRATION_DATABASE_URL).set(database=TEST_DB_NAME)
    runtime_url = make_url(settings.DATABASE_URL).set(database=TEST_DB_NAME)

    alembic_cfg = Config(str(ALEMBIC_INI))
    alembic_cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        migration_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    with patch.object(settings, "DB_NAME", TEST_DB_NAME):
        command.upgrade(alembic_cfg, "head")
    engine = create_engine(runtime_url)

    yield engine
    engine.dispose()

    admin_engine2 = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine2.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
    admin_engine2.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Создать новую сессию для каждого теста."""
    SessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    """Создать тестовый клиент FastAPI."""

    def skip_smtp(
        service: EmailService, to: str, subject: str, body_text: str
    ) -> None:
        return None

    monkeypatch.setattr(EmailService, "_send_smtp", skip_smtp)

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    # Integration callers use the Bearer API contract and send same-origin
    # metadata as a browser behind the configured local Vite proxy would.
    return TestClient(
        app,
        headers={
            "Origin": settings.FRONTEND_URL,
            "X-Return-Bearer-Token": "true",
        },
    )


@pytest.fixture
def auth_headers(client):
    """Зарегистрировать пользователя и получить заголовки с токеном."""
    resp = client.post(
        "/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "secret123",
            "full_name": "Test User",
        },
    )
    data = resp.json()
    token = data["data"]["token"]
    return {"Authorization": f"Bearer {token}"}
