"""Интеграционные тесты дашборда."""

from fastapi.testclient import TestClient


class TestDashboard:
    def test_summary(self, client: TestClient, auth_headers):
        """Получить сводку дашборда."""
        resp = client.get("/v1/dashboard/summary", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "monthly_expected_income" in data["data"]
        assert "outstanding_balance" in data["data"]
        assert "occupancy_rate" in data["data"]
        assert "overdue_count" in data["data"]
        assert "overdue_total_amount" in data["data"]
        assert isinstance(data["data"]["overdue_count"], int)

    def test_no_token(self, client: TestClient):
        """Без токена — 422."""
        resp = client.get("/v1/dashboard/summary")
        assert resp.status_code in (401, 403, 422)
