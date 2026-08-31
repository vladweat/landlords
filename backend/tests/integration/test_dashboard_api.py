"""Интеграционные тесты дашборда."""
from datetime import datetime

from fastapi.testclient import TestClient


class TestDashboard:
    def test_summary(self, client: TestClient, auth_headers):
        """Получить сводку дашборда."""
        resp = client.get("/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "monthly_expected_income" in data["data"]
        assert "outstanding_balance" in data["data"]
        assert "occupancy_rate" in data["data"]

    def test_no_token(self, client: TestClient):
        """Без токена — 422."""
        resp = client.get("/dashboard/summary")
        assert resp.status_code in (401, 403, 422)