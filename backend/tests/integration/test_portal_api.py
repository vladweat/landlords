"""Интеграционные тесты публичного портала арендатора."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models.contract_model import ContractModel
from app.db.models.rent_charge_model import RentChargeModel
from tests.integration.conftest import property_payload


@pytest.fixture(autouse=True)
def _portal_invoice_storage(tmp_path, monkeypatch):
    storage = tmp_path / "documents"
    storage.mkdir()
    monkeypatch.setattr("app.services.pdf_service.STORAGE_DIR", str(storage))
    monkeypatch.setattr("app.services.document_service.STORAGE_DIR", str(storage))
    return storage


def _create_property(client, headers):
    resp = client.post(
        "/v1/properties",
        json=property_payload(street="Портал"),
        headers=headers,
    )
    return resp.json()["data"]["id"]


def _create_tenant(client, headers):
    resp = client.post(
        "/v1/tenants",
        json={"full_name": "Арендатор Портала"},
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
            "rent_amount": "35000.00",
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
        amount=Decimal("35000.00"),
        currency="RUB",
        status="pending",
    )
    db_session.add(model)
    db_session.flush()
    return charge_id


class TestPortalApi:
    def test_ensure_public_claim_dismiss(self, client: TestClient, auth_headers, db_session):
        contract_id = _create_active_contract(client, auth_headers)
        account_id = _account_id(client, auth_headers)
        _insert_charge(db_session, account_id, contract_id)

        client.patch(
            "/v1/account",
            json={"payment_details": "СБП 900"},
            headers=auth_headers,
        )

        ensure = client.post(
            f"/v1/contracts/{contract_id}/portal",
            headers=auth_headers,
        )
        assert ensure.status_code == 200
        data = ensure.json()["data"]
        token = data["portal_token"]
        assert data["share_url"].endswith(f"/t/{token}")
        expires_at = datetime.fromisoformat(data["portal_token_expires_at"])
        assert timedelta(hours=1, minutes=55) < expires_at - datetime.now(timezone.utc)
        assert expires_at - datetime.now(timezone.utc) <= timedelta(hours=2)

        again = client.post(
            f"/v1/contracts/{contract_id}/portal",
            headers=auth_headers,
        )
        assert again.json()["data"]["portal_token"] == token

        public = client.get(f"/v1/public/portal/{token}")
        assert public.status_code == 200
        body = public.json()["data"]
        assert body["tenant_name"] == "Арендатор Портала"
        assert body["outstanding_balance"] == "35000.00"
        assert body["payment_details"] == "СБП 900"
        assert body["pending_claim"] is None
        assert len(body["open_charges"]) == 1
        assert body["open_charges"][0]["invoice_url"] is not None

        no_amount = client.post(
            f"/v1/public/portal/{token}/claim",
            json={"note": "без суммы"},
        )
        assert no_amount.status_code == 422

        claim = client.post(
            f"/v1/public/portal/{token}/claim",
            json={"amount": "35000.00", "note": "Оплатил сегодня"},
        )
        assert claim.status_code == 201
        claim_id = claim.json()["data"]["id"]
        assert claim.json()["data"]["status"] == "pending"
        assert claim.json()["data"]["amount"] == "35000.00"

        dup = client.post(
            f"/v1/public/portal/{token}/claim",
            json={"amount": "35000.00"},
        )
        assert dup.status_code == 409

        public2 = client.get(f"/v1/public/portal/{token}")
        assert public2.json()["data"]["pending_claim"]["id"] == claim_id

        claims = client.get(
            f"/v1/contracts/{contract_id}/claims",
            params={"status": "pending"},
            headers=auth_headers,
        )
        assert claims.status_code == 200
        assert len(claims.json()["data"]) == 1

        events = client.get(
            f"/v1/contracts/{contract_id}/events",
            headers=auth_headers,
        )
        types = [e["event_type"] for e in events.json()["data"]["items"]]
        assert "payment_claim" in types

        dismiss = client.post(
            f"/v1/claims/{claim_id}/dismiss",
            headers=auth_headers,
        )
        assert dismiss.status_code == 200
        assert dismiss.json()["data"]["status"] == "dismissed"

        claim2 = client.post(
            f"/v1/public/portal/{token}/claim",
            json={"amount": "35000.00"},
        )
        assert claim2.status_code == 201
        claim2_id = claim2.json()["data"]["id"]

        confirm = client.post(
            f"/v1/claims/{claim2_id}/confirm",
            headers=auth_headers,
        )
        assert confirm.status_code == 200
        assert confirm.json()["data"]["status"] == "confirmed"

        ledger = client.get(
            f"/v1/contracts/{contract_id}/ledger",
            headers=auth_headers,
        )
        assert ledger.status_code == 200
        assert ledger.json()["data"]["outstanding_balance"] == "0.00"
        assert ledger.json()["data"]["total_paid"] == "35000.00"

        payments = client.get(
            "/v1/payments",
            params={"contract_id": contract_id},
            headers=auth_headers,
        )
        assert payments.status_code == 200
        assert len(payments.json()["data"]) >= 1

    def test_expired_portal_link_is_rejected_and_ensure_renews_it(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id = _create_active_contract(client, auth_headers)
        ensured = client.post(
            f"/v1/contracts/{contract_id}/portal", headers=auth_headers
        )
        old_token = ensured.json()["data"]["portal_token"]
        contract = db_session.query(ContractModel).filter_by(id=contract_id).one()
        contract.portal_token_expires_at = datetime.now(timezone.utc) - timedelta(
            seconds=1
        )
        db_session.flush()

        assert client.get(f"/v1/public/portal/{old_token}").status_code == 404
        assert client.post(
            f"/v1/public/portal/{old_token}/claim", json={"amount": "100.00"}
        ).status_code == 404

        renewed = client.post(
            f"/v1/contracts/{contract_id}/portal", headers=auth_headers
        )
        new_data = renewed.json()["data"]
        assert new_data["portal_token"] != old_token
        assert (
            client.get(f"/v1/public/portal/{new_data['portal_token']}").status_code
            == 200
        )

    def test_rotate_invalidates_old_token(self, client: TestClient, auth_headers):
        contract_id = _create_active_contract(client, auth_headers)
        ensure = client.post(
            f"/v1/contracts/{contract_id}/portal",
            headers=auth_headers,
        )
        old_token = ensure.json()["data"]["portal_token"]

        rotated = client.post(
            f"/v1/contracts/{contract_id}/portal/rotate",
            headers=auth_headers,
        )
        rotated_data = rotated.json()["data"]
        new_token = rotated_data["portal_token"]
        assert new_token != old_token
        assert timedelta(hours=1, minutes=55) < (
            datetime.fromisoformat(rotated_data["portal_token_expires_at"])
            - datetime.now(timezone.utc)
        )

        assert client.get(f"/v1/public/portal/{old_token}").status_code == 404
        assert client.get(f"/v1/public/portal/{new_token}").status_code == 200

    def test_terminated_contract_revokes_public_portal_access(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id = _create_active_contract(client, auth_headers)
        ensured = client.post(
            f"/v1/contracts/{contract_id}/portal", headers=auth_headers
        )
        token = ensured.json()["data"]["portal_token"]

        terminated = client.post(
            f"/v1/contracts/{contract_id}/terminate",
            headers=auth_headers,
            json={
                "effective_date": date.today().isoformat(),
                "termination_reason": "test",
                "generate_act": False,
            },
        )
        assert terminated.status_code == 200, terminated.text
        contract = db_session.query(ContractModel).filter_by(id=contract_id).one()
        assert contract.portal_token is None

        assert client.get(f"/v1/public/portal/{token}").status_code == 404
        assert client.post(
            f"/v1/public/portal/{token}/claim", json={"amount": "100.00"}
        ).status_code == 404

    def test_public_404(self, client: TestClient):
        resp = client.get("/v1/public/portal/not-a-real-token")
        assert resp.status_code == 404
