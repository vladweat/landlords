"""Интеграционные тесты вложений."""

from datetime import date, timedelta
from io import BytesIO

from fastapi.testclient import TestClient

from tests.integration.conftest import property_payload


def _create_property(client, headers, street="Вложения"):
    resp = client.post(
        "/v1/properties",
        json=property_payload(street=street),
        headers=headers,
    )
    return resp.json()["data"]["id"]


def _create_tenant(client, headers, name="Арендатор Вложений"):
    resp = client.post("/v1/tenants", json={"full_name": name}, headers=headers)
    return resp.json()["data"]["id"]


def _create_active_contract(client, headers):
    property_id = _create_property(client, headers)
    tenant_id = _create_tenant(client, headers)
    start = date.today() - timedelta(days=10)
    end = date.today() + timedelta(days=200)
    create = client.post(
        "/v1/contracts",
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": str(start),
            "end_date": str(end),
            "rent_amount": "40000.00",
            "payment_day": 5,
        },
        headers=headers,
    )
    contract_id = create.json()["data"]["id"]
    client.put(
        f"/v1/contracts/{contract_id}",
        json={"status": "active"},
        headers=headers,
    )
    return contract_id, property_id


class TestDocumentsApi:
    def test_list_empty_contract(self, client: TestClient, auth_headers):
        contract_id, _ = _create_active_contract(client, auth_headers)
        resp = client.get(f"/v1/contracts/{contract_id}/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    def test_upload_list_download_delete_contract(self, client: TestClient, auth_headers):
        contract_id, _ = _create_active_contract(client, auth_headers)
        files = {"file": ("scan.pdf", BytesIO(b"%PDF-1.4 hello"), "application/pdf")}
        data = {"category": "passport", "title": "Паспорт"}
        upload = client.post(
            f"/v1/contracts/{contract_id}/documents",
            headers=auth_headers,
            files=files,
            data=data,
        )
        assert upload.status_code == 200
        doc = upload.json()["data"]
        assert doc["category"] == "passport"
        assert doc["source"] == "uploaded"
        assert doc["mime_type"] == "application/pdf"
        assert doc["title"] == "Паспорт"
        assert doc["url"].endswith(f"/documents/{doc['id']}")

        listed = client.get(f"/v1/contracts/{contract_id}/documents", headers=auth_headers)
        assert len(listed.json()["data"]) == 1

        download = client.get(f"/v1/documents/{doc['id']}", headers=auth_headers)
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("application/pdf")
        assert download.content.startswith(b"%PDF")

        deleted = client.delete(f"/v1/documents/{doc['id']}", headers=auth_headers)
        assert deleted.status_code == 200
        listed2 = client.get(f"/v1/contracts/{contract_id}/documents", headers=auth_headers)
        assert listed2.json()["data"] == []

    def test_upload_property(self, client: TestClient, auth_headers):
        property_id = _create_property(client, auth_headers, street="Фотообъект")
        files = {"file": ("room.png", BytesIO(b"\x89PNG\r\n"), "image/png")}
        data = {"category": "photo"}
        upload = client.post(
            f"/v1/properties/{property_id}/documents",
            headers=auth_headers,
            files=files,
            data=data,
        )
        assert upload.status_code == 200
        doc = upload.json()["data"]
        assert doc["property_id"] == property_id
        assert doc["category"] == "photo"

        listed = client.get(
            f"/v1/properties/{property_id}/documents", headers=auth_headers
        )
        assert len(listed.json()["data"]) == 1

    def test_reject_bad_mime(self, client: TestClient, auth_headers):
        contract_id, _ = _create_active_contract(client, auth_headers)
        files = {"file": ("x.bin", BytesIO(b"\x00\x01"), "application/octet-stream")}
        resp = client.post(
            f"/v1/contracts/{contract_id}/documents",
            headers=auth_headers,
            files=files,
            data={"category": "other"},
        )
        assert resp.status_code == 422

    def test_no_token(self, client: TestClient):
        resp = client.get(f"/v1/documents/{'0'*8}-{'0'*4}-{'0'*4}-{'0'*4}-{'0'*12}")
        assert resp.status_code in (401, 403, 422)
