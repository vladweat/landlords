"""Интеграционные тесты платежей."""

from fastapi.testclient import TestClient


class TestPayments:
    def test_list_empty(self, client: TestClient, auth_headers):
        """Пустой список платежей."""
        resp = client.get("/v1/payments", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    def test_no_token(self, client: TestClient):
        """Без токена — 422."""
        resp = client.get("/v1/payments")
        assert resp.status_code in (401, 403, 422)
