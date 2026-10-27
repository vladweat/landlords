"""Transactional outbox coverage for contract API producers."""

from datetime import date, timedelta
from uuid import UUID, uuid4

from app.db.models.contract_model import ContractModel
from app.db.models.outbox_message_model import OutboxMessageModel
from app.db.models.user_model import UserModel
from app.db.session import get_db_session
from tests.integration.conftest import property_payload


TASK_NAME = "app.tasks.charge_tasks.generate_charges_for_contract"


def _create_contract(client, headers, *, auto_generate_charges=False):
    property_response = client.post(
        "/v1/properties",
        json=property_payload(street="Outbox API"),
        headers=headers,
    )
    tenant_response = client.post(
        "/v1/tenants",
        json={"full_name": "Outbox Tenant"},
        headers=headers,
    )
    assert property_response.status_code == 201
    assert tenant_response.status_code == 201
    start = date.today() - timedelta(days=30)
    end = date.today() + timedelta(days=300)
    response = client.post(
        "/v1/contracts",
        json={
            "property_id": property_response.json()["data"]["id"],
            "tenant_id": tenant_response.json()["data"]["id"],
            "start_date": str(start),
            "end_date": str(end),
            "rent_amount": 45000,
            "payment_day": 5,
            "auto_generate_charges": auto_generate_charges,
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def test_single_endpoint_returns_persisted_outbox_id(client, auth_headers, db_session):
    contract_id = _create_contract(client, auth_headers)

    response = client.post(
        f"/v1/contracts/{contract_id}/generate-charges", headers=auth_headers
    )

    assert response.status_code == 200
    task_id = UUID(response.json()["data"]["task_id"])
    row = db_session.get(OutboxMessageModel, task_id)
    assert row is not None
    assert str(row.contract_id) == contract_id
    assert row.task_name == TASK_NAME


def test_single_endpoint_does_not_enqueue_contract_outside_account(
    client, auth_headers, db_session
):
    response = client.post(
        f"/v1/contracts/{uuid4()}/generate-charges", headers=auth_headers
    )

    assert response.status_code == 404
    assert db_session.query(OutboxMessageModel).count() == 0


def test_activation_and_outbox_row_rollback_together(
    client, auth_headers, db_session
):
    contract_id = _create_contract(client, auth_headers, auto_generate_charges=True)
    user = db_session.query(UserModel).filter_by(email="test@example.com").one()
    user.email = f"test+{uuid4().hex}@example.com"
    db_session.commit()
    previous_override = client.app.dependency_overrides[get_db_session]

    def rollback_request_session():
        try:
            yield db_session
        finally:
            db_session.rollback()

    client.app.dependency_overrides[get_db_session] = rollback_request_session
    try:
        response = client.put(
            f"/v1/contracts/{contract_id}",
            json={"status": "active"},
            headers=auth_headers,
        )
    finally:
        client.app.dependency_overrides[get_db_session] = previous_override

    assert response.status_code == 200
    contract = db_session.get(ContractModel, UUID(contract_id))
    assert contract is not None
    assert contract.status == "draft"
    assert (
        db_session.query(OutboxMessageModel)
        .filter(OutboxMessageModel.contract_id == UUID(contract_id))
        .count()
        == 0
    )


def test_activation_with_auto_generation_persists_same_outbox_task(
    client, auth_headers, db_session
):
    contract_id = _create_contract(client, auth_headers, auto_generate_charges=True)

    response = client.put(
        f"/v1/contracts/{contract_id}",
        json={"status": "active"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "active"
    row = (
        db_session.query(OutboxMessageModel)
        .filter(OutboxMessageModel.contract_id == UUID(contract_id))
        .one()
    )
    assert row.status == "pending"
    assert row.task_name == TASK_NAME
