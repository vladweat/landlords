"""Интеграционные тесты RBAC и команды аккаунта."""

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


def _register(client: TestClient, email: str, name: str = "User") -> dict:
    resp = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secret123", "full_name": name},
    )
    assert resp.status_code == 200
    return resp.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestMeIncludesRole:
    def test_me_returns_account_and_role(self, client: TestClient, auth_headers):
        resp = client.get("/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["user"]["email"] == "test@example.com"
        assert data["role"] == "owner"
        assert "id" in data["account"]
        assert data["account"]["name"]


class TestTeamMembers:
    def test_owner_creates_and_lists_members(self, client: TestClient, auth_headers):
        create = client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "manager@example.com",
                "full_name": "Manager",
                "password": "secret123",
                "role": "manager",
            },
        )
        assert create.status_code == 201
        member = create.json()["data"]
        assert member["role"] == "manager"
        assert member["email"] == "manager@example.com"

        listed = client.get("/v1/account/members", headers=auth_headers)
        assert listed.status_code == 200
        emails = [m["email"] for m in listed.json()["data"]]
        assert "manager@example.com" in emails
        assert "test@example.com" in emails

    def test_member_login_and_shared_account(self, client: TestClient, auth_headers):
        client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "acc@example.com",
                "full_name": "Accountant",
                "password": "secret123",
                "role": "accountant",
            },
        )
        # Owner creates property
        prop = client.post(
            "/v1/properties",
            headers=auth_headers,
            json=property_payload(street="Shared"),
        )
        assert prop.status_code == 201

        login = client.post(
            "/v1/auth/login",
            json={"email": "acc@example.com", "password": "secret123"},
        )
        assert login.status_code == 200
        member_headers = _headers(login.json()["token"])

        me = client.get("/v1/auth/me", headers=member_headers)
        assert me.json()["data"]["role"] == "accountant"

        props = client.get("/v1/properties", headers=member_headers)
        assert props.status_code == 200
        addresses = [p["address"] for p in props.json()["data"]["items"]]
        assert any("Shared" in a for a in addresses)

    def test_accountant_forbidden_create_property(self, client: TestClient, auth_headers):
        client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "acc2@example.com",
                "full_name": "Acc",
                "password": "secret123",
                "role": "accountant",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "acc2@example.com", "password": "secret123"},
        )
        member_headers = _headers(login.json()["token"])

        # Read ok
        assert client.get("/v1/properties", headers=member_headers).status_code == 200
        # Write forbidden
        resp = client.post(
            "/v1/properties",
            headers=member_headers,
            json=property_payload(street="No"),
        )
        assert resp.status_code == 403

    def test_manager_can_create_property_not_team(self, client: TestClient, auth_headers):
        client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "mgr@example.com",
                "full_name": "Mgr",
                "password": "secret123",
                "role": "manager",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "mgr@example.com", "password": "secret123"},
        )
        member_headers = _headers(login.json()["token"])

        prop = client.post(
            "/v1/properties",
            headers=member_headers,
            json=property_payload(street="Mgr Prop"),
        )
        assert prop.status_code == 201

        team = client.get("/v1/account/members", headers=member_headers)
        assert team.status_code == 403

    def test_remove_member_blocks_login(self, client: TestClient, auth_headers):
        created = client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "temp@example.com",
                "full_name": "Temp",
                "password": "secret123",
                "role": "manager",
            },
        )
        user_id = created.json()["data"]["user_id"]

        delete = client.delete(
            f"/v1/account/members/{user_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        login = client.post(
            "/v1/auth/login",
            json={"email": "temp@example.com", "password": "secret123"},
        )
        assert login.status_code == 401

    def test_non_owner_cannot_delete_account(self, client: TestClient, auth_headers):
        client.post(
            "/v1/account/members",
            headers=auth_headers,
            json={
                "email": "mgrdel@example.com",
                "full_name": "Mgr",
                "password": "secret123",
                "role": "manager",
            },
        )
        login = client.post(
            "/v1/auth/login",
            json={"email": "mgrdel@example.com", "password": "secret123"},
        )
        member_headers = _headers(login.json()["token"])
        resp = client.request(
            "DELETE",
            "/v1/auth/me",
            headers=member_headers,
            json={"confirmation": "DELETE"},
        )
        assert resp.status_code == 403


class TestMemberIsolation:
    def test_member_does_not_see_other_account(self, client: TestClient):
        owner_a = _register(client, "ownera@test.com", "Owner A")
        headers_a = _headers(owner_a["token"])
        client.post(
            "/v1/account/members",
            headers=headers_a,
            json={
                "email": "membera@test.com",
                "full_name": "Member A",
                "password": "secret123",
                "role": "manager",
            },
        )
        client.post(
            "/v1/properties",
            headers=headers_a,
            json=property_payload(street="Only A"),
        )

        owner_b = _register(client, "ownerb@test.com", "Owner B")
        headers_b = _headers(owner_b["token"])
        client.post(
            "/v1/properties",
            headers=headers_b,
            json=property_payload(street="Only B"),
        )

        login = client.post(
            "/v1/auth/login",
            json={"email": "membera@test.com", "password": "secret123"},
        )
        member_headers = _headers(login.json()["token"])
        props = client.get("/v1/properties", headers=member_headers)
        addresses = [p["address"] for p in props.json()["data"]["items"]]
        assert any("Only A" in a for a in addresses)
        assert all("Only B" not in a for a in addresses)
