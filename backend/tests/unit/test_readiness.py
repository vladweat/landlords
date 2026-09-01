from fastapi.testclient import TestClient

import redis

from app.main import create_app


class DummyRedis:
    def ping(self):
        return True


def test_readiness_ok(monkeypatch):
    app = create_app()
    # monkeypatch redis.from_url to return dummy redis
    monkeypatch.setattr(redis, "from_url", lambda url: DummyRedis())

    client = TestClient(app)
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

