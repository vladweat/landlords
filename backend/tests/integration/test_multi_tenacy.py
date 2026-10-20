"""Тесты multi-tenancy изоляции."""

from datetime import date, timedelta
from io import BytesIO
import json
import zipfile

from fastapi.testclient import TestClient

from app.db.models.contract_model import ContractModel
from app.db.models.document_model import DocumentModel
from app.db.models.property_expense_model import PropertyExpenseModel
from app.db.models.property_model import PropertyModel
from app.db.models.tenant_model import TenantModel

from tests.integration.conftest import property_payload


def _account_id(client: TestClient, headers: dict) -> str:
    return client.get("/v1/auth/me", headers=headers).json()["data"]["account"]["id"]


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

    def test_contract_rejects_foreign_property_or_tenant(self, client, db_session):
        """Нельзя связать договор своего tenant с чужим ресурсом через подмену ID."""
        a = client.post("/v1/auth/register", json={
            "email": "contract-a@test.com", "password": "secret123", "full_name": "A"
        }).json()
        b = client.post("/v1/auth/register", json={
            "email": "contract-b@test.com", "password": "secret123", "full_name": "B"
        }).json()
        headers_a = {"Authorization": f"Bearer {a['token']}"}
        headers_b = {"Authorization": f"Bearer {b['token']}"}
        property_a = client.post("/v1/properties", headers=headers_a,
            json=property_payload(street="A")).json()["data"]["id"]
        tenant_a = client.post("/v1/tenants", headers=headers_a,
            json={"full_name": "Tenant A"}).json()["data"]["id"]
        property_b = client.post("/v1/properties", headers=headers_b,
            json=property_payload(street="B")).json()["data"]["id"]
        tenant_b = client.post("/v1/tenants", headers=headers_b,
            json={"full_name": "Tenant B"}).json()["data"]["id"]
        start = date.today() + timedelta(days=30)
        body = {"property_id": property_a, "tenant_id": tenant_a,
            "start_date": str(start), "end_date": str(start + timedelta(days=365)),
            "rent_amount": "1000", "payment_day": 5}

        for changed in (
            {**body, "property_id": property_b},
            {**body, "tenant_id": tenant_b},
        ):
            response = client.post("/v1/contracts", headers=headers_a, json=changed)
            assert response.status_code == 404

        forged_context = client.post("/v1/contracts", headers=headers_a,
            json={**body, "account_id": _account_id(client, headers_b)})
        assert forged_context.status_code == 201
        assert forged_context.json()["data"]["account_id"] == _account_id(client, headers_a)
        assert db_session.query(ContractModel).count() == 1
        assert db_session.query(TenantModel).filter_by(id=tenant_a).one().account_id == db_session.query(
            PropertyModel
        ).filter_by(id=property_a).one().account_id

    def test_foreign_parent_filters_and_expense_idor_do_not_change_data(
        self, client, db_session
    ):
        """Подмена property/expense ID не раскрывает данные и не меняет чужую запись."""
        a = client.post("/v1/auth/register", json={
            "email": "expense-a@test.com", "password": "secret123", "full_name": "A"
        }).json()
        b = client.post("/v1/auth/register", json={
            "email": "expense-b@test.com", "password": "secret123", "full_name": "B"
        }).json()
        headers_a = {"Authorization": f"Bearer {a['token']}"}
        headers_b = {"Authorization": f"Bearer {b['token']}"}
        prop_b = client.post("/v1/properties", headers=headers_b,
            json=property_payload(street="Private B")).json()["data"]["id"]
        created = client.post("/v1/expenses", headers=headers_b, json={
            "property_id": prop_b, "category": "repair", "amount": "1200",
            "date_incurred": date.today().isoformat(), "note": "private note",
        })
        assert created.status_code == 201
        expense_id = created.json()["data"]["id"]

        assert client.get(f"/v1/expenses?property_id={prop_b}", headers=headers_a).json()["data"] == []
        assert client.put(f"/v1/expenses/{expense_id}", headers=headers_a,
            json={"note": "modified"}).status_code == 404
        assert client.delete(f"/v1/expenses/{expense_id}", headers=headers_a).status_code == 404
        assert db_session.query(PropertyExpenseModel).filter_by(id=expense_id).one().note == "private note"
        assert str(db_session.query(PropertyModel).filter_by(id=prop_b).one().account_id) != _account_id(client, headers_a)

    def test_cross_tenant_contract_ids_cannot_read_update_delete_or_open_ledger(
        self, client, db_session
    ):
        a = client.post("/v1/auth/register", json={
            "email": "contract-read-a@test.com", "password": "secret123", "full_name": "A"
        }).json()
        b = client.post("/v1/auth/register", json={
            "email": "contract-read-b@test.com", "password": "secret123", "full_name": "B"
        }).json()
        headers_a = {"Authorization": f"Bearer {a['token']}"}
        headers_b = {"Authorization": f"Bearer {b['token']}"}
        prop_b = client.post("/v1/properties", headers=headers_b,
            json=property_payload(street="Contract B")).json()["data"]["id"]
        tenant_b = client.post("/v1/tenants", headers=headers_b,
            json={"full_name": "Tenant B"}).json()["data"]["id"]
        start = date.today() + timedelta(days=30)
        contract = client.post("/v1/contracts", headers=headers_b, json={
            "property_id": prop_b, "tenant_id": tenant_b,
            "start_date": str(start), "end_date": str(start + timedelta(days=365)),
            "rent_amount": "23000", "payment_day": 5,
        })
        assert contract.status_code == 201
        contract_id = contract.json()["data"]["id"]
        tenants_a = client.get("/v1/tenants", headers=headers_a).json()["data"]["items"]
        contracts_a = client.get("/v1/contracts", headers=headers_a).json()["data"]["items"]
        assert all(item["id"] != tenant_b for item in tenants_a)
        assert all(item["id"] != contract_id for item in contracts_a)

        assert client.get(f"/v1/contracts/{contract_id}", headers=headers_a).status_code == 404
        assert client.get(f"/v1/contracts/{contract_id}/ledger", headers=headers_a).status_code == 404
        assert client.put(f"/v1/contracts/{contract_id}", headers=headers_a,
            json={"rent_amount": "1"}).status_code == 404
        assert client.delete(f"/v1/contracts/{contract_id}", headers=headers_a).status_code == 404
        assert client.get(f"/v1/contracts/{contract_id}/documents", headers=headers_a).status_code == 404
        report = client.get(
            f"/v1/reports/export?start_date={date.today().isoformat()}"
            f"&end_date={(date.today() + timedelta(days=365)).isoformat()}"
            f"&format=csv&contract_ids={contract_id}",
            headers=headers_a,
        )
        assert report.status_code == 200
        assert contract_id.encode() not in report.content
        account_export = client.get("/v1/account/export", headers=headers_a)
        assert account_export.status_code == 200
        with zipfile.ZipFile(BytesIO(account_export.content)) as archive:
            payload = json.loads(archive.read("account_export.json"))
        assert all(item["id"] != contract_id for item in payload["contracts"])
        assert all(item["id"] != prop_b for item in payload["properties"])
        stored = db_session.query(ContractModel).filter_by(id=contract_id).one()
        assert str(stored.account_id) == _account_id(client, headers_b)
        assert str(stored.account_id) != _account_id(client, headers_a)
        assert str(stored.rent_amount) == "23000.00"

    def test_foreign_document_download_and_delete_are_denied(self, client, db_session):
        """Чужой document ID не даёт скачать или удалить файл другого аккаунта."""
        owner = client.post("/v1/auth/register", json={
            "email": "document-owner@test.com", "password": "secret123", "full_name": "Owner"
        }).json()
        other = client.post("/v1/auth/register", json={
            "email": "document-other@test.com", "password": "secret123", "full_name": "Other"
        }).json()
        owner_headers = {"Authorization": f"Bearer {owner['token']}"}
        other_headers = {"Authorization": f"Bearer {other['token']}"}
        prop = client.post("/v1/properties", headers=owner_headers,
            json=property_payload(street="Document owner")).json()["data"]["id"]
        upload = client.post(f"/v1/properties/{prop}/documents", headers=owner_headers,
            files={"file": ("private.pdf", BytesIO(b"%PDF private"), "application/pdf")},
            data={"category": "other"})
        assert upload.status_code == 200
        doc_id = upload.json()["data"]["id"]
        document = db_session.query(DocumentModel).filter_by(id=doc_id).one()
        original_path = document.file_path

        download = client.get(f"/v1/documents/{doc_id}", headers=other_headers)
        assert download.status_code == 404
        assert client.delete(f"/v1/documents/{doc_id}", headers=other_headers).status_code == 404
        db_session.refresh(document)
        assert document.file_path == original_path
        assert str(document.account_id) == _account_id(client, owner_headers)
