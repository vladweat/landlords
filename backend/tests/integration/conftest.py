"""Фикстуры для интеграционных тестов внутри Docker-контейнера."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.base import Base
from app.db.session import get_db_session
from app.main import create_app

TEST_DB_NAME = "landlords_test"


@pytest.fixture(scope="session")
def test_engine():
    """Создать тестовую БД и движок."""
    # Создаём тестовую БД
    admin_url = settings.DATABASE_URL.replace(settings.DB_NAME, "postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB_NAME}"))
    admin_engine.dispose()

    # Подключаемся к тестовой БД
    test_url = settings.DATABASE_URL.replace(settings.DB_NAME, TEST_DB_NAME)
    engine = create_engine(test_url)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

    # Чистим
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
def client(db_session):
    """Создать тестовый клиент FastAPI."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app = create_app()
    app.dependency_overrides[get_db_session] = override_get_db
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Зарегистрировать пользователя и получить заголовки с токеном."""
    resp = client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "password": "secret123",
            "full_name": "Test User",
        },
    )
    data = resp.json()
    token = data["token"]
    return {"Authorization": f"Bearer {token}"}