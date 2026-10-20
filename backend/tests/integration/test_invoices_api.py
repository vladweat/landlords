"""Интеграционные тесты квитанций."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models.invoice_model import InvoiceModel
from app.db.models.rent_charge_model import RentChargeModel
from tests.integration.conftest import property_payload


@pytest.fixture(autouse=True)
def _invoice_storage(tmp_path, monkeypatch):
    """Писать PDF квитанций во временную директорию."""
    storage = tmp_path / "documents"
    storage.mkdir()
    monkeypatch.setattr("app.services.pdf_service.STORAGE_DIR", str(storage))
    return storage


def _create_property(client, headers):
    resp = client.post(
        "/v1/properties",
        json=property_payload(street="Квитанция"),
        headers=headers,
    )
    return resp.json()["data"]["id"]


def _create_tenant(client, headers):
    resp = client.post(
        "/v1/tenants",
        json={"full_name": "Арендатор Квитанции"},
        headers=headers,
    )
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
            "rent_amount": "45000.00",
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
    return contract_id


def _account_id(client, headers) -> UUID:
    me = client.get("/v1/auth/me", headers=headers)
    return UUID(me.json()["data"]["account"]["id"])


def _insert_charge(db_session, account_id: UUID, contract_id: UUID) -> UUID:
    charge_id = uuid4()
    model = RentChargeModel(
        id=charge_id,
        account_id=account_id,
        contract_id=UUID(contract_id) if isinstance(contract_id, str) else contract_id,
        due_date=date.today() + timedelta(days=5),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("45000.00"),
        currency="RUB",
        status="pending",
    )
    db_session.add(model)
    db_session.flush()
    return charge_id


class TestInvoicesApi:
    def test_create_and_public_get(self, client: TestClient, auth_headers, db_session):
        contract_id = _create_active_contract(client, auth_headers)
        account_id = _account_id(client, auth_headers)
        charge_id = _insert_charge(db_session, account_id, contract_id)

        client.patch(
            "/v1/account",
            json={"payment_details": "Карта 2200 · Иванов И.И."},
            headers=auth_headers,
        )

        create = client.post(
            f"/v1/charges/{charge_id}/invoice",
            headers=auth_headers,
        )
        assert create.status_code == 200
        data = create.json()["data"]
        assert data["charge_id"] == str(charge_id)
        assert data["share_url"].endswith(f"/i/{data['public_token']}")
        assert data["document_id"] is not None
        assert datetime.fromisoformat(data["public_token_expires_at"]) > datetime.now(
            timezone.utc
        )
        token = data["public_token"]

        again = client.post(
            f"/v1/charges/{charge_id}/invoice",
            headers=auth_headers,
        )
        assert again.status_code == 200
        assert again.json()["data"]["public_token"] == token

        got = client.get(
            f"/v1/charges/{charge_id}/invoice",
            headers=auth_headers,
        )
        assert got.status_code == 200
        assert got.json()["data"]["public_token"] == token

        public = client.get(f"/v1/public/invoices/{token}")
        assert public.status_code == 200
        body = public.json()["data"]
        assert body["amount"] == "45000.00"
        assert body["amount_remaining"] == "45000.00"
        assert body["tenant_name"] == "Арендатор Квитанции"
        assert body["payment_details"] == "Карта 2200 · Иванов И.И."
        assert "phone" not in body

        pdf = client.get(f"/v1/public/invoices/{token}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content[:4] == b"%PDF"

        rotated = client.post(
            f"/v1/charges/{charge_id}/invoice/rotate-link",
            headers=auth_headers,
        )
        assert rotated.status_code == 200
        new_token = rotated.json()["data"]["public_token"]
        assert new_token != token
        assert client.get(f"/v1/public/invoices/{token}").status_code == 404
        assert client.get(f"/v1/public/invoices/{token}/pdf").status_code == 404
        assert client.get(f"/v1/public/invoices/{new_token}").status_code == 200

    def test_expired_invoice_link_is_rejected_on_all_public_routes(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id = _create_active_contract(client, auth_headers)
        account_id = _account_id(client, auth_headers)
        charge_id = _insert_charge(db_session, account_id, contract_id)
        created = client.post(
            f"/v1/charges/{charge_id}/invoice", headers=auth_headers
        )
        assert created.status_code == 200
        token = created.json()["data"]["public_token"]
        invoice = (
            db_session.query(InvoiceModel)
            .filter_by(public_token=token)
            .one()
        )
        invoice.public_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db_session.flush()

        assert client.get(f"/v1/public/invoices/{token}").status_code == 404
        assert client.get(f"/v1/public/invoices/{token}/pdf").status_code == 404
        assert client.post(
            f"/v1/public/invoices/{token}/claim", json={"amount": "100.00"}
        ).status_code == 404

    def test_public_404(self, client: TestClient):
        resp = client.get("/v1/public/invoices/not-a-real-token")
        assert resp.status_code == 404
