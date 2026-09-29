"""Интеграционные тесты тарифов и лимитов."""

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


def _register(client: TestClient, email: str) -> dict:
    resp = client.post(
        "/v1/auth/register",
        json={
            "email": email,
            "password": "secret123",
            "full_name": "Owner",
        },
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestPlansApi:
    def test_me_includes_plan(self, client: TestClient, auth_headers):
        resp = client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"]["account"]["plan"] == "free"

    def test_get_subscription(self, client: TestClient, auth_headers):
        resp = client.get("/v1/account/subscription", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["plan"] == "free"
        assert data["limits"]["max_properties"] == 3
        assert data["usage"]["properties"] == 0
        assert len(data["plans_catalog"]) == 3

    def test_change_plan_owner(self, client: TestClient, auth_headers):
        resp = client.patch(
            "/v1/account/plan",
            json={"plan": "pro"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["plan"] == "pro"

        sub = client.get("/v1/account/subscription", headers=auth_headers)
        assert sub.json()["data"]["plan"] == "pro"
        assert sub.json()["data"]["limits"]["max_properties"] == 25

    def test_change_plan_invalid(self, client: TestClient, auth_headers):
        resp = client.patch(
            "/v1/account/plan",
            json={"plan": "gold"},
            headers=auth_headers,
        )
        assert resp.status_code == 422
        assert "тариф" in resp.json()["message"].lower()

    def test_property_limit_free(self, client: TestClient):
        headers = _register(client, "plan-props@example.com")
        for i in range(3):
            resp = client.post(
                "/v1/properties",
                json=property_payload(street=f"Улица{i}", house=str(i + 1)),
                headers=headers,
            )
            assert resp.status_code == 201, resp.text

        blocked = client.post(
            "/v1/properties",
            json=property_payload(street="Лишняя", house="99"),
            headers=headers,
        )
        assert blocked.status_code == 422
        assert "лимит" in blocked.json()["message"].lower()

    def test_invite_limit_free(self, client: TestClient):
        headers = _register(client, "plan-invite@example.com")
        ok = client.post(
            "/v1/account/invites",
            json={
                "email": "mgr-plan@example.com",
                "full_name": "Manager",
                "role": "manager",
            },
            headers=headers,
        )
        assert ok.status_code == 201, ok.text

        blocked = client.post(
            "/v1/account/invites",
            json={
                "email": "acc-plan@example.com",
                "full_name": "Accountant",
                "role": "accountant",
            },
            headers=headers,
        )
        assert blocked.status_code == 422
        assert "лимит" in blocked.json()["message"].lower()

    def test_manager_cannot_change_plan(self, client: TestClient):
        owner_headers = _register(client, "plan-owner-rbac@example.com")
        client.patch(
            "/v1/account/plan",
            json={"plan": "pro"},
            headers=owner_headers,
        )
        invite = client.post(
            "/v1/account/invites",
            json={
                "email": "plan-mgr-rbac@example.com",
                "full_name": "Mgr",
                "role": "manager",
            },
            headers=owner_headers,
        )
        assert invite.status_code == 201
        token = invite.json()["data"]["token"]

        accept = client.post(
            f"/v1/public/invites/{token}/accept",
            json={"password": "secret123", "full_name": "Mgr"},
        )
        assert accept.status_code == 200, accept.text
        mgr_token = accept.json()["token"]
        mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

        resp = client.patch(
            "/v1/account/plan",
            json={"plan": "enterprise"},
            headers=mgr_headers,
        )
        assert resp.status_code == 403
