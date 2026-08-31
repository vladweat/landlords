"""Интеграционные тесты CRUD арендаторов."""

from fastapi.testclient import TestClient


class TestTenantsCRUD:
    def test_create_tenant(self, client: TestClient, auth_headers):
        """Создать арендатора."""
        resp = client.post(
            "/tenants",
            json={
                "full_name": "Петров Пётр",
                "email": "petrov@example.com",
                "phone": "+79998887766",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["full_name"] == "Петров Пётр"

    def test_list_tenants(self, client: TestClient, auth_headers):
        """Получить список арендаторов."""
        client.post(
            "/tenants",
            json={"full_name": "Сидоров Сидор"},
            headers=auth_headers,
        )
        resp = client.get("/tenants", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_get_tenant(self, client: TestClient, auth_headers):
        """Получить арендатора по ID."""
        create = client.post(
            "/tenants",
            json={"full_name": "Иванов Иван"},
            headers=auth_headers,
        )
        tenant_id = create.json()["data"]["id"]
        resp = client.get(f"/tenants/{tenant_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Иванов Иван"

    def test_update_tenant(self, client: TestClient, auth_headers):
        """Обновить арендатора."""
        create = client.post(
            "/tenants",
            json={"full_name": "Старое Имя"},
            headers=auth_headers,
        )
        tenant_id = create.json()["data"]["id"]
        resp = client.put(
            f"/tenants/{tenant_id}",
            json={"full_name": "Новое Имя", "is_active": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["full_name"] == "Новое Имя"
        assert resp.json()["data"]["is_active"] is False

    def test_delete_tenant(self, client: TestClient, auth_headers):
        """Удалить арендатора."""
        create = client.post(
            "/tenants",
            json={"full_name": "Удаляемый"},
            headers=auth_headers,
        )
        tenant_id = create.json()["data"]["id"]
        resp = client.delete(f"/tenants/{tenant_id}", headers=auth_headers)
        assert resp.status_code == 204

    def test_tenant_not_found(self, client: TestClient, auth_headers):
        """Арендатор не найден."""
        resp = client.get(
            "/tenants/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404