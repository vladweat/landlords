"""Интеграционные тесты CRUD объектов недвижимости."""

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


class TestPropertiesCRUD:
    def test_create_property(self, client: TestClient, auth_headers):
        """Создать объект недвижимости."""
        resp = client.post(
            "/v1/properties",
            json=property_payload(
                street="Тестовая",
                house="1",
                purchase_price=3000000,
            ),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["city"] == "Москва"
        assert data["data"]["street"] == "Тестовая"
        assert data["data"]["house"] == "1"
        assert data["data"]["type"] == "apartment"

    def test_list_properties(self, client: TestClient, auth_headers):
        """Получить список объектов."""
        client.post(
            "/v1/properties",
            json=property_payload(street="Списка", house="1", property_type="house", size_m2=100.0),
            headers=auth_headers,
        )
        resp = client.get("/v1/properties", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()["data"]["items"]) >= 1

    def test_get_property(self, client: TestClient, auth_headers):
        """Получить объект по ID."""
        create = client.post(
            "/v1/properties",
            json=property_payload(street="Поиск", house="1", property_type="room", size_m2=20.0),
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.get(f"/v1/properties/{prop_id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == prop_id

    def test_update_property(self, client: TestClient, auth_headers):
        """Обновить объект."""
        create = client.post(
            "/v1/properties",
            json=property_payload(street="Апдейт", house="1", size_m2=40.0),
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.put(
            f"/v1/properties/{prop_id}",
            json={"street": "Апдейт", "house": "2", "status": "inactive"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["street"] == "Апдейт"
        assert resp.json()["data"]["house"] == "2"

    def test_delete_property(self, client: TestClient, auth_headers):
        """Удалить объект."""
        create = client.post(
            "/v1/properties",
            json=property_payload(street="Удаления", house="1", property_type="room", size_m2=15.0),
            headers=auth_headers,
        )
        prop_id = create.json()["data"]["id"]
        resp = client.delete(f"/v1/properties/{prop_id}", headers=auth_headers)
        assert resp.status_code == 204

        get_resp = client.get(f"/v1/properties/{prop_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_property_not_found(self, client: TestClient, auth_headers):
        """Объект не найден."""
        resp = client.get(
            "/v1/properties/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_invalid_type(self, client: TestClient, auth_headers):
        """Невалидный тип недвижимости."""
        resp = client.post(
            "/v1/properties",
            json=property_payload(street="Ошибок", house="1", property_type="castle", size_m2=100.0),
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_negative_size(self, client: TestClient, auth_headers):
        """Отрицательная площадь."""
        resp = client.post(
            "/v1/properties",
            json=property_payload(street="Минус", house="1", size_m2=-10.0),
            headers=auth_headers,
        )
        assert resp.status_code == 422
