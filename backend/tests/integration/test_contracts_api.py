"""Интеграционные тесты контрактов."""

from datetime import date, timedelta, datetime
from decimal import Decimal
from fastapi.testclient import TestClient


def _create_property(client, headers, address="ул. Тест"):
    resp = client.post(
        "/properties",
        json={"address": address, "type": "apartment", "size_m2": 50.0},
        headers=headers,
    )
    return resp.json()["data"]["id"]


def _create_tenant(client, headers, name="Тестовый"):
    resp = client.post(
        "/tenants",
        json={"full_name": name},
        headers=headers,
    )
    return resp.json()["data"]["id"]


class TestContractsCRUD:
    def test_create_contract(self, client: TestClient, auth_headers):
        """Создать контракт."""
        property_id = _create_property(client, auth_headers)
        tenant_id = _create_tenant(client, auth_headers)

        start = date.today() + timedelta(days=30)
        end = date(start.year + 1, start.month, start.day)
        resp = client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 50000,
                "payment_day": 5,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["status"] == "draft"
        
        assert Decimal(resp.json()["data"]["rent_amount"]) == Decimal("50000")

    def test_list_contracts(self, client: TestClient, auth_headers):
        """Получить список контрактов."""
        property_id = _create_property(client, auth_headers, "ул. Списка")
        tenant_id = _create_tenant(client, auth_headers, "Списочный")
        start = date.today() + timedelta(days=60)
        end = date(start.year + 1, start.month, start.day)
        client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 30000,
                "payment_day": 10,
            },
            headers=auth_headers,
        )
        resp = client.get("/contracts", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_activate_contract(self, client: TestClient, auth_headers):
        """Активировать контракт."""
        property_id = _create_property(client, auth_headers, "ул. Активация")
        tenant_id = _create_tenant(client, auth_headers, "Активный")
        start = date.today() + timedelta(days=30)
        end = date(start.year + 1, start.month, start.day)
        create = client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 40000,
                "payment_day": 15,
            },
            headers=auth_headers,
        )
        contract_id = create.json()["data"]["id"]
        resp = client.put(
            f"/contracts/{contract_id}",
            json={"status": "active"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["status"] == "active"

    def test_conflict_two_active_contracts(self, client: TestClient, auth_headers):
        """Нельзя создать второй активный контракт на тот же объект."""
        property_id = _create_property(client, auth_headers, "ул. Конфликт")
        tenant1 = _create_tenant(client, auth_headers, "Первый")
        tenant2 = _create_tenant(client, auth_headers, "Второй")
        start = date.today() + timedelta(days=30)
        end = date(start.year + 1, start.month, start.day)

        create = client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant1,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 40000,
                "payment_day": 15,
            },
            headers=auth_headers,
        )
        contract_id = create.json()["data"]["id"]
        client.put(
            f"/contracts/{contract_id}",
            json={"status": "active"},
            headers=auth_headers,
        )

        # Пытаемся создать второй активный контракт
        resp = client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant2,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 50000,
                "payment_day": 5,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_delete_contract(self, client: TestClient, auth_headers):
        """Удалить контракт (draft)."""
        property_id = _create_property(client, auth_headers, "ул. Удаление")
        tenant_id = _create_tenant(client, auth_headers, "Удаляемый")
        start = date.today() + timedelta(days=30)
        end = date(start.year + 1, start.month, start.day)
        create = client.post(
            "/contracts",
            json={
                "property_id": property_id,
                "tenant_id": tenant_id,
                "start_date": str(start),
                "end_date": str(end),
                "rent_amount": 50000,
                "payment_day": 5,
            },
            headers=auth_headers,
        )
        contract_id = create.json()["data"]["id"]
        resp = client.delete(f"/contracts/{contract_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_contract_not_found(self, client: TestClient, auth_headers):
        """Контракт не найден."""
        resp = client.get(
            "/contracts/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404