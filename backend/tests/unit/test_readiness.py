from unittest.mock import MagicMock

from fastapi.testclient import TestClient

import redis

from app.main import create_app


class DummyRedis:
    def ping(self):
        return True


def test_readiness_ok(monkeypatch):
    app = create_app()
    monkeypatch.setattr(redis, "from_url", lambda url: DummyRedis())
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: MagicMock())

    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_closes_session_when_database_probe_fails(monkeypatch):
    class FailingSession:
        closed = False

        def __enter__(self) -> "FailingSession":
            return self

        def __exit__(self, *args: object) -> None:
            self.closed = True

        def execute(self, statement: object) -> None:
            raise RuntimeError("database unavailable")

    session = FailingSession()
    monkeypatch.setattr("app.db.session.SessionLocal", lambda: session)

    client = TestClient(create_app())
    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["message"] == "db_unavailable"
    assert session.closed
