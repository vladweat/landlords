"""Интеграционные тесты начислений."""

from fastapi.testclient import TestClient


class TestCharges:
    def test_list_empty(self, client: TestClient, auth_headers):
        """Пустой список начислений."""
        resp = client.get("/v1/charges", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_no_token(self, client: TestClient):
        """Без токена — 422."""
        resp = client.get("/v1/charges")
        assert resp.status_code in (401, 403, 422)
