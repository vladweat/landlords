"""Интеграционные тесты CRUD объектов недвижимости."""

from fastapi.testclient import TestClient


class TestPropertiesCRUD:
    def test_create_property(self, client: TestClient, auth_headers):
        """Создать объект недвижимости."""
        resp = client.post(
            "/properties",
            json={
                "address": "ул. Тестовая, д. 1",
                "type": "apartment",
                "size_m2": 50.0,
                "purchase_price": 3000000,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["address"] == "ул. Тестовая, д. 1"
        assert data["data"]["type"] == "apartment"

    def test_list_properties(self, client: TestClient, auth_headers):
        """Получить список объектов."""
        client.post(
            "/properties",
            json={"address": "ул. Списка, д. 1", "type": "house", "size_m2": 100.0},
            headers=auth_headers,
        )
        resp = client.get("/properties", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 1

    def test_get_property(self, client: TestClient, auth_headers):
        """Получить объект по ID."""
        create = client.post(
            "/properties",
            json={"address": "ул. Поиск, д. 1", "type": "room", "size_m2": 20.0},
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.get(f"/properties/{prop_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == prop_id

    def test_update_property(self, client: TestClient, auth_headers):
        """Обновить объект."""
        create = client.post(
            "/properties",
            json={"address": "ул. Апдейт, д. 1", "type": "apartment", "size_m2": 40.0},
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.put(
            f"/properties/{prop_id}",
            json={"address": "ул. Апдейт, д. 2", "status": "inactive"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["address"] == "ул. Апдейт, д. 2"

    def test_delete_property(self, client: TestClient, auth_headers):
        """Удалить объект."""
        create = client.post(
            "/properties",
            json={"address": "ул. Удаления, д. 1", "type": "room", "size_m2": 15.0},
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.delete(f"/properties/{prop_id}", headers=auth_headers)
        assert resp.status_code == 204

        get_resp = client.get(f"/properties/{prop_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_property_not_found(self, client: TestClient, auth_headers):
        """Объект не найден."""
        resp = client.get(
            "/properties/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_invalid_type(self, client: TestClient, auth_headers):
        """Невалидный тип недвижимости."""
        resp = client.post(
            "/properties",
            json={"address": "ул. Ошибок, д. 1", "type": "castle", "size_m2": 100.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_negative_size(self, client: TestClient, auth_headers):
        """Отрицательная площадь."""
        resp = client.post(
            "/properties",
            json={"address": "ул. Минус, д. 1", "type": "apartment", "size_m2": -10.0},
            headers=auth_headers,
        )
        assert resp.status_code == 422