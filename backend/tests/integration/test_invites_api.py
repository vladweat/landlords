"""Интеграционные тесты invite-flow."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.account_invite_model import AccountInviteModel


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestInvitesApi:
    def test_create_preview_accept(self, client: TestClient, auth_headers):
        create = client.post(
            "/v1/account/invites",
            headers=auth_headers,
            json={
                "email": "newmgr@example.com",
                "full_name": "New Manager",
                "role": "manager",
            },
        )
        assert create.status_code == 201
        data = create.json()["data"]
        assert data["email"] == "newmgr@example.com"
        assert data["role"] == "manager"
        assert "token" in data
        assert "/invite?token=" in data["invite_url"]
        token = data["token"]

        listed = client.get("/v1/account/invites", headers=auth_headers)
        assert listed.status_code == 200
        assert any(i["email"] == "newmgr@example.com" for i in listed.json()["data"])

        preview = client.get(f"/v1/public/invites/{token}")
        assert preview.status_code == 200
        assert preview.json()["data"]["email"] == "newmgr@example.com"
        assert preview.json()["data"]["role"] == "manager"

        accept = client.post(
            f"/v1/public/invites/{token}/accept",
            json={"password": "secret123"},
        )
        assert accept.status_code == 200
        assert accept.json()["user"]["email"] == "newmgr@example.com"
        assert "token" in accept.json()

        me = client.get("/v1/auth/me", headers=_headers(accept.json()["token"]))
        assert me.status_code == 200
        assert me.json()["data"]["role"] == "manager"

        # повторный accept — gone
        again = client.post(
            f"/v1/public/invites/{token}/accept",
            json={"password": "secret123"},
        )
        assert again.status_code == 410

    def test_conflict_existing_email(self, client: TestClient, auth_headers):
        resp = client.post(
            "/v1/account/invites",
            headers=auth_headers,
            json={
                "email": "test@example.com",
                "full_name": "Dup",
                "role": "manager",
            },
        )
        assert resp.status_code == 409

    def test_revoke(self, client: TestClient, auth_headers):
        create = client.post(
            "/v1/account/invites",
            headers=auth_headers,
            json={
                "email": "revoked@example.com",
                "full_name": "Revoked",
                "role": "accountant",
            },
        )
        invite_id = create.json()["data"]["id"]
        token = create.json()["data"]["token"]

        delete = client.delete(
            f"/v1/account/invites/{invite_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        preview = client.get(f"/v1/public/invites/{token}")
        assert preview.status_code == 404

    def test_expired_invite(self, client: TestClient, auth_headers, db_session: Session):
        create = client.post(
            "/v1/account/invites",
            headers=auth_headers,
            json={
                "email": "expired@example.com",
                "full_name": "Expired",
                "role": "manager",
            },
        )
        token = create.json()["data"]["token"]

        row = db_session.query(AccountInviteModel).filter_by(token=token).one()
        row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.flush()

        preview = client.get(f"/v1/public/invites/{token}")
        assert preview.status_code == 410
