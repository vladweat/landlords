"""Интеграционные тесты RBAC и команды аккаунта."""

from datetime import date, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.db.models.account_model import AccountModel
from app.db.models.contract_model import ContractModel
from app.db.models.membership_model import MembershipModel
from app.db.models.user_model import UserModel

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


def _invite_and_accept(
    client: TestClient,
    owner_headers: dict,
    email: str,
    role: str = "manager",
    name: str = "Member",
    password: str = "secret123",
) -> dict:
    """Создать invite и принять — возвращает AuthResponse принявшего."""
    create = client.post(
        "/v1/account/invites",
        headers=owner_headers,
        json={"email": email, "full_name": name, "role": role},
    )
    assert create.status_code == 201, create.text
    token = create.json()["data"]["token"]
    accept = client.post(
        f"/v1/public/invites/{token}/accept",
        json={"password": password, "full_name": name},
    )
    assert accept.status_code == 200, accept.text
    return accept.json()


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
    def test_owner_invites_and_lists_members(self, client: TestClient, auth_headers):
        accepted = _invite_and_accept(
            client, auth_headers, "manager@example.com", role="manager", name="Manager"
        )
        assert accepted["data"]["user"]["email"] == "manager@example.com"

        listed = client.get("/v1/account/members", headers=auth_headers)
        assert listed.status_code == 200
        emails = [m["email"] for m in listed.json()["data"]]
        assert "manager@example.com" in emails
        assert "test@example.com" in emails

    def test_member_login_and_shared_account(self, client: TestClient, auth_headers):
        _invite_and_accept(
            client, auth_headers, "acc@example.com", role="accountant", name="Accountant"
        )
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
        member_headers = _headers(login.json()["data"]["token"])

        me = client.get("/v1/auth/me", headers=member_headers)
        assert me.json()["data"]["role"] == "accountant"

        props = client.get("/v1/properties", headers=member_headers)
        assert props.status_code == 200
        addresses = [p["address"] for p in props.json()["data"]["items"]]
        assert any("Shared" in a for a in addresses)

    def test_accountant_forbidden_create_property(
        self, client: TestClient, auth_headers, db_session
    ):
        accepted = _invite_and_accept(
            client, auth_headers, "acc2@example.com", role="accountant", name="Acc"
        )
        member_headers = _headers(accepted["data"]["token"])

        assert client.get("/v1/properties", headers=member_headers).status_code == 200
        resp = client.post(
            "/v1/properties",
            headers=member_headers,
            json=property_payload(street="No"),
        )
        assert resp.status_code == 403

        property_id = client.post(
            "/v1/properties", headers=auth_headers,
            json=property_payload(street="Contract target"),
        ).json()["data"]["id"]
        tenant_id = client.post(
            "/v1/tenants", headers=auth_headers,
            json={"full_name": "Contract target"},
        ).json()["data"]["id"]
        start_date = date.today() + timedelta(days=30)
        contract_response = client.post("/v1/contracts", headers=member_headers, json={
            "property_id": property_id, "tenant_id": tenant_id,
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=365)),
            "rent_amount": "10000", "payment_day": 5,
        })
        assert contract_response.status_code == 403
        account_response = client.get("/v1/auth/me", headers=auth_headers)
        account_id = UUID(account_response.json()["data"]["account"]["id"])
        assert db_session.query(ContractModel).filter_by(
            account_id=account_id,
            property_id=UUID(property_id),
            tenant_id=UUID(tenant_id),
        ).count() == 0

    def test_manager_can_create_property_not_team(self, client: TestClient, auth_headers):
        accepted = _invite_and_accept(
            client, auth_headers, "mgr@example.com", role="manager", name="Mgr"
        )
        member_headers = _headers(accepted["data"]["token"])

        prop = client.post(
            "/v1/properties",
            headers=member_headers,
            json=property_payload(street="Mgr Prop"),
        )
        assert prop.status_code == 201

        team = client.get("/v1/account/members", headers=member_headers)
        assert team.status_code == 403

    def test_remove_member_blocks_login(self, client: TestClient, auth_headers):
        accepted = _invite_and_accept(
            client, auth_headers, "temp@example.com", role="manager", name="Temp"
        )
        user_id = accepted["data"]["user"]["id"]
        stale_member_headers = _headers(accepted["data"]["token"])

        delete = client.delete(
            f"/v1/account/members/{user_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204
        assert client.get("/v1/auth/me", headers=stale_member_headers).status_code == 401

        login = client.post(
            "/v1/auth/login",
            json={"email": "temp@example.com", "password": "secret123"},
        )
        assert login.status_code == 401

    def test_remove_member_deletes_member_but_preserves_tenant_data(
        self, client: TestClient, auth_headers, db_session
    ):
        accepted = _invite_and_accept(
            client, auth_headers, "retained-member@example.com", role="manager", name="Retained"
        )
        user_id = accepted["data"]["user"]["id"]
        property_response = client.post(
            "/v1/properties", headers=auth_headers,
            json=property_payload(street="Must remain"),
        )
        assert property_response.status_code == 201
        account_id = client.get("/v1/auth/me", headers=auth_headers).json()["data"]["account"]["id"]

        response = client.delete(f"/v1/account/members/{user_id}", headers=auth_headers)
        assert response.status_code == 204
        assert db_session.query(AccountModel).filter_by(id=account_id).one_or_none() is not None
        assert db_session.query(MembershipModel).filter_by(user_id=user_id).one_or_none() is None
        assert db_session.query(UserModel).filter_by(id=user_id).one_or_none() is None
        listed = client.get("/v1/properties", headers=auth_headers)
        assert any("Must remain" in item["address"] for item in listed.json()["data"]["items"])

    def test_non_owner_cannot_delete_account(self, client: TestClient, auth_headers):
        accepted = _invite_and_accept(
            client, auth_headers, "mgrdel@example.com", role="manager", name="Mgr"
        )
        member_headers = _headers(accepted["data"]["token"])
        resp = client.request(
            "DELETE",
            "/v1/auth/me",
            headers=member_headers,
            json={"confirmation": "DELETE"},
        )
        assert resp.status_code == 403

    def test_owner_cannot_change_or_remove_member_from_another_account(
        self, client: TestClient, db_session
    ):
        owner_a = _register(client, "admin-a@test.com", "Owner A")
        owner_b = _register(client, "admin-b@test.com", "Owner B")
        headers_a = _headers(owner_a["data"]["token"])
        headers_b = _headers(owner_b["data"]["token"])
        member = _invite_and_accept(
            client, headers_b, "admin-target@test.com", role="manager", name="Target"
        )
        target_id = member["data"]["user"]["id"]

        change = client.patch(f"/v1/account/members/{target_id}", headers=headers_a,
            json={"role": "accountant"})
        remove = client.delete(f"/v1/account/members/{target_id}", headers=headers_a)
        assert change.status_code == 404
        assert remove.status_code == 404

        login = client.post("/v1/auth/login", json={
            "email": "admin-target@test.com", "password": "secret123"
        })
        assert login.status_code == 200
        me = client.get("/v1/auth/me", headers=_headers(login.json()["data"]["token"]))
        assert me.json()["data"]["role"] == "manager"
        assert db_session.query(AccountModel).filter_by(
            id=me.json()["data"]["account"]["id"]
        ).one_or_none() is not None


class TestMemberIsolation:
    def test_member_does_not_see_other_account(self, client: TestClient):
        owner_a = _register(client, "ownera@test.com", "Owner A")
        headers_a = _headers(owner_a["data"]["token"])
        _invite_and_accept(
            client, headers_a, "membera@test.com", role="manager", name="Member A"
        )
        client.post(
            "/v1/properties",
            headers=headers_a,
            json=property_payload(street="Only A"),
        )

        owner_b = _register(client, "ownerb@test.com", "Owner B")
        headers_b = _headers(owner_b["data"]["token"])
        client.post(
            "/v1/properties",
            headers=headers_b,
            json=property_payload(street="Only B"),
        )

        login = client.post(
            "/v1/auth/login",
            json={"email": "membera@test.com", "password": "secret123"},
        )
        member_headers = _headers(login.json()["data"]["token"])
        props = client.get("/v1/properties", headers=member_headers)
        addresses = [p["address"] for p in props.json()["data"]["items"]]
        assert any("Only A" in a for a in addresses)
        assert all("Only B" not in a for a in addresses)
