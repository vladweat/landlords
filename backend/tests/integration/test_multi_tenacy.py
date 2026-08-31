"""Тесты multi-tenancy изоляции."""

from fastapi.testclient import TestClient


class TestMultiTenancyIsolation:
    def test_users_see_only_own_data(self, client: TestClient):
        """Пользователи видят только свои данные."""
        # Пользователь A
        a = client.post(
            "/auth/register",
            json={"email": "a@test.com", "password": "secret", "full_name": "A"},
        )
        token_a = a.json()["token"]
        headers_a = {"Authorization": f"Bearer {token_a}"}

        # Пользователь B
        b = client.post(
            "/auth/register",
            json={"email": "b@test.com", "password": "secret", "full_name": "B"},
        )
        token_b = b.json()["token"]
        headers_b = {"Authorization": f"Bearer {token_b}"}

        # A создаёт property
        client.post(
            "/properties",
            json={"address": "Только A", "type": "apartment", "size_m2": 50},
            headers=headers_a,
        )

        # B создаёт property
        client.post(
            "/properties",
            json={"address": "Только B", "type": "house", "size_m2": 100},
            headers=headers_b,
        )

        # A видит только своё
        resp_a_list = client.get("/properties", headers=headers_a)
        addresses_a = [p["address"] for p in resp_a_list.json()["data"]["items"]]
        assert "Только A" in addresses_a
        assert "Только B" not in addresses_a

        # B видит только своё
        resp_b = client.get("/properties", headers=headers_b)
        addresses_b = [p["address"] for p in resp_b.json()["data"]["items"]]
        assert "Только B" in addresses_b
        assert "Только A" not in addresses_b