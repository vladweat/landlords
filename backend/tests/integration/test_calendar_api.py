"""Интеграционные тесты календаря платежей."""

from datetime import date, timedelta

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


def _create_property(client, headers, street="Календарная"):
    resp = client.post(
        "/v1/properties",
        json=property_payload(street=street),
        headers=headers,
    )
    return resp.json()["data"]["id"]


def _create_tenant(client, headers, name="Календарный"):
    resp = client.post(
        "/v1/tenants",
        json={"full_name": name},
        headers=headers,
    )
    return resp.json()["data"]["id"]


class TestCalendarApi:
    def test_empty_events(self, client: TestClient, auth_headers):
        """Пустой календарь для нового аккаунта."""
        resp = client.get("/v1/calendar/events", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["data"]["items"] == []

    def test_contract_ending_event(self, client: TestClient, auth_headers):
        """Активный договор с end_date в окне → contract_ending."""
        property_id = _create_property(client, auth_headers)
        tenant_id = _create_tenant(client, auth_headers)
        start = date.today() - timedelta(days=30)
        end = date.today() + timedelta(days=15)
        create = client.post(
            "/v1/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": "45000.00",
                "payment_day": 5,
            },
            headers=auth_headers,
        )
        contract_id = create.json()["data"]["id"]
        client.put(
            f"/v1/contracts/{contract_id}",
            json={"status": "active"},
            headers=auth_headers,
        )

        today = date.today()
        resp = client.get(
            "/v1/calendar/events",
            params={"from": str(today), "to": str(today + timedelta(days=45))},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        items = resp.json()["data"]["items"]
        endings = [i for i in items if i["type"] == "contract_ending"]
        assert len(endings) == 1
        assert endings[0]["contract_id"] == contract_id
        assert endings[0]["rent_amount"] == "45000.00"
        assert endings[0]["tenant_name"] == "Календарный"

    def test_no_token(self, client: TestClient):
        """Без токена — отказ."""
        resp = client.get("/v1/calendar/events")
        assert resp.status_code in (401, 403, 422)
