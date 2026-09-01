"""Интеграционные тесты расходов по объектам."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


def _create_property(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/v1/properties",
        json=property_payload(street="Расходная", purchase_price=5000000),
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


class TestExpenses:
    def test_list_empty(self, client: TestClient, auth_headers):
        resp = client.get("/v1/expenses", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_create_and_list(self, client: TestClient, auth_headers):
        property_id = _create_property(client, auth_headers)
        resp = client.post(
            "/v1/expenses",
            json={
                "property_id": property_id,
                "category": "utilities",
                "amount": "3500.00",
                "date_incurred": date.today().isoformat(),
                "note": "ЖКХ за месяц",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["category"] == "utilities"
        assert Decimal(str(data["amount"])) == Decimal("3500.00")

        listed = client.get("/v1/expenses", headers=auth_headers)
        assert listed.status_code == 200
        assert len(listed.json()["data"]) == 1

    def test_filter_by_property(self, client: TestClient, auth_headers):
        prop_a = _create_property(client, auth_headers)
        prop_b = client.post(
            "/v1/properties",
            json=property_payload(street="Другая"),
            headers=auth_headers,
        ).json()["data"]["id"]

        client.post(
            "/v1/expenses",
            json={
                "property_id": prop_a,
                "category": "repair",
                "amount": "10000",
                "date_incurred": date.today().isoformat(),
            },
            headers=auth_headers,
        )
        client.post(
            "/v1/expenses",
            json={
                "property_id": prop_b,
                "category": "tax",
                "amount": "20000",
                "date_incurred": date.today().isoformat(),
            },
            headers=auth_headers,
        )

        resp = client.get(f"/v1/expenses?property_id={prop_a}", headers=auth_headers)
        assert resp.status_code == 200
        items = resp.json()["data"]
        assert len(items) == 1
        assert items[0]["property_id"] == prop_a

    def test_delete(self, client: TestClient, auth_headers):
        property_id = _create_property(client, auth_headers)
        created = client.post(
            "/v1/expenses",
            json={
                "property_id": property_id,
                "category": "realtor_fee",
                "amount": "50000",
                "date_incurred": date.today().isoformat(),
            },
            headers=auth_headers,
        ).json()["data"]

        resp = client.delete(f"/v1/expenses/{created['id']}", headers=auth_headers)
        assert resp.status_code == 204

        listed = client.get("/v1/expenses", headers=auth_headers)
        assert listed.json()["data"] == []

    def test_invalid_category(self, client: TestClient, auth_headers):
        property_id = _create_property(client, auth_headers)
        resp = client.post(
            "/v1/expenses",
            json={
                "property_id": property_id,
                "category": "food",
                "amount": "100",
                "date_incurred": date.today().isoformat(),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_roi_includes_expenses(self, client: TestClient, auth_headers):
        """ROI учитывает расходы: прибыль = доход − расход."""
        property_id = _create_property(client, auth_headers)
        client.post(
            "/v1/expenses",
            json={
                "property_id": property_id,
                "category": "tax",
                "amount": "100000",
                "date_incurred": date.today().isoformat(),
            },
            headers=auth_headers,
        )

        resp = client.get(f"/v1/properties/{property_id}", headers=auth_headers)
        assert resp.status_code == 200
        roi = resp.json()["data"]["roi"]
        assert "annual_expenses" in roi
        assert float(roi["annual_expenses"]) == 100000.0
