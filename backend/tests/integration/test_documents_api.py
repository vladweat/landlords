"""Интеграционные тесты вложений."""

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.db.models.document_model import DocumentModel
from app.db.session import get_db_session
from tests.integration.conftest import property_payload


@pytest.fixture(autouse=True)
def document_storage(tmp_path, monkeypatch):
    storage = tmp_path / "documents"
    storage.mkdir()
    monkeypatch.setattr("app.services.document_service.STORAGE_DIR", str(storage))
    monkeypatch.setattr("app.services.pdf_service.STORAGE_DIR", str(storage))
    return storage


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
    def test_contract_document_generation_is_not_available_over_get(
        self, client: TestClient, auth_headers
    ):
        response = client.get(
            "/v1/contracts/00000000-0000-0000-0000-000000000001/document",
            headers=auth_headers,
        )

        assert response.status_code == 405

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
        assert download.headers["x-content-type-options"] == "nosniff"
        assert download.content.startswith(b"%PDF")

        deleted = client.delete(f"/v1/documents/{doc['id']}", headers=auth_headers)
        assert deleted.status_code == 200
        listed2 = client.get(f"/v1/contracts/{contract_id}/documents", headers=auth_headers)
        assert listed2.json()["data"] == []

    def test_transaction_rollback_leaves_file_for_reconciliation(
        self, client: TestClient, auth_headers, db_session, document_storage
    ):
        contract_id, _ = _create_active_contract(client, auth_headers)

        def fail_commit():
            try:
                yield db_session
            except Exception:
                db_session.rollback()
                raise
            db_session.rollback()
            raise SQLAlchemyError("simulated commit failure")

        client.app.dependency_overrides[get_db_session] = fail_commit
        failing_client = TestClient(client.app, raise_server_exceptions=False)
        upload = failing_client.post(
            f"/v1/contracts/{contract_id}/documents",
            headers=auth_headers,
            files={
                "file": (
                    "scan.pdf",
                    BytesIO(b"%PDF-1.4 rollback"),
                    "application/pdf",
                )
            },
            data={"category": "other"},
        )
        assert upload.status_code == 500
        assert db_session.query(DocumentModel).count() == 0
        assert len(list(document_storage.rglob("*.pdf"))) == 1

    def test_download_rejects_path_outside_storage(
        self, client: TestClient, auth_headers, db_session, tmp_path
    ):
        contract_id, _ = _create_active_contract(client, auth_headers)
        upload = client.post(
            f"/v1/contracts/{contract_id}/documents",
            headers=auth_headers,
            files={
                "file": (
                    "scan.pdf",
                    BytesIO(b"%PDF-1.4 data"),
                    "application/pdf",
                )
            },
            data={"category": "other"},
        )
        doc_id = upload.json()["data"]["id"]
        document = db_session.query(DocumentModel).filter_by(id=doc_id).one()
        outside = tmp_path / "private.pdf"
        outside.write_bytes(b"%PDF private")
        document.file_path = str(outside)
        db_session.flush()

        response = client.get(f"/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_upload_property(self, client: TestClient, auth_headers):
        property_id = _create_property(client, auth_headers, street="Фотообъект")
        files = {
            "file": (
                "room.png",
                BytesIO(b"\x89PNG\r\n\x1a\n"),
                "image/png",
            )
        }
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
