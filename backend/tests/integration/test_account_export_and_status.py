"""Интеграция: выгрузка аккаунта и публичный статус."""

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload
from tests.integration.test_rbac_api import _headers, _invite_and_accept, _register


def test_owner_can_export_account(client: TestClient, auth_headers):
    client.post("/v1/properties", headers=auth_headers, json=property_payload())
    resp = client.get("/v1/account/export", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert resp.content[:2] == b"PK"


def test_non_owner_cannot_export(client: TestClient, auth_headers):
    accepted = _invite_and_accept(
        client, auth_headers, "mgr-export@example.com", role="manager", name="Mgr"
    )
    member_headers = _headers(accepted["data"]["token"])
    resp = client.get("/v1/account/export", headers=member_headers)
    assert resp.status_code == 403


def test_public_status(client: TestClient):
    resp = client.get("/v1/public/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["data"]["overall"] in ("operational", "degraded", "outage")
    assert "incidents" in body["data"]
    assert "support_email" in body["data"]


def test_register_still_works(client: TestClient):
    data = _register(client, "export-owner@example.com", "Export Owner")
    assert "token" in data["data"]
