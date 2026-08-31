"""Тесты multi-tenancy изоляции."""

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


class TestMultiTenancyIsolation:
    def test_users_see_only_own_data(self, client: TestClient):
        """Пользователи видят только свои данные."""
        a = client.post(
            "/v1/auth/register",
            json={"email": "a@test.com", "password": "secret", "full_name": "A"},
        )
        token_a = a.json()["token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        b = client.post(
            "/v1/auth/register",
            json={"email": "b@test.com", "password": "secret", "full_name": "B"},
        )
        token_b = b.json()["token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        client.post(
            "/v1/properties",
            json=property_payload(street="Только A"),
            headers=headers_a,
        )

        client.post(
            "/v1/properties",
            json=property_payload(street="Только B", property_type="house", size_m2=100),
            headers=headers_b,
        )

        resp_a_list = client.get("/v1/properties", headers=headers_a)
        addresses_a = [p["address"] for p in resp_a_list.json()["data"]["items"]]
        assert any("Только A" in address for address in addresses_a)
        assert all("Только B" not in address for address in addresses_a)

        resp_b = client.get("/v1/properties", headers=headers_b)
        addresses_b = [p["address"] for p in resp_b.json()["data"]["items"]]
        assert any("Только B" in address for address in addresses_b)
        assert all("Только A" not in address for address in addresses_b)
