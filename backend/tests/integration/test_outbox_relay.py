"""PostgreSQL lease and task-completion guarantees for the outbox."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import sessionmaker

from app.db.models.contract_model import ContractModel
from app.db.models.outbox_message_model import OutboxMessageModel
from app.db.models.rent_charge_model import RentChargeModel
from app.db.models.user_model import UserModel
from app.db.repositories.outbox_message_repo import OutboxMessageRepository
from app.db.tenant_context import set_tenant_context
from app.tasks.charge_tasks import generate_charges_for_contract
from tests.integration.test_outbox_api import _create_contract


def _rename_committed_test_user(db_session):
    user = db_session.query(UserModel).filter_by(email="test@example.com").one()
    user.email = f"test+{uuid4().hex}@example.com"


def test_relay_lease_blocks_second_claim_and_expired_lease_is_recoverable(
    client, auth_headers, db_session, test_engine
):
    contract_id = _create_contract(client, auth_headers)
    contract_uuid = UUID(contract_id)
    account_id = UUID(client.get("/v1/auth/me", headers=auth_headers).json()["data"]["account"]["id"])
    set_tenant_context(db_session, account_id)
    contract = db_session.get(ContractModel, contract_uuid)
    task_id = OutboxMessageRepository(db_session).create_charge_generation(
        account_id, contract_uuid
    )
    _rename_committed_test_user(db_session)
    db_session.commit()

    set_tenant_context(db_session, account_id)
    first_claim = OutboxMessageRepository(db_session).claim_due_batch(10, 30)
    assert [message.id for message in first_claim] == [task_id]
    db_session.commit()

    other_session = sessionmaker(bind=test_engine)()
    try:
        set_tenant_context(other_session, account_id)
        second_claim = OutboxMessageRepository(other_session).claim_due_batch(10, 30)
        assert second_claim == []
        other_session.commit()
    finally:
        other_session.close()

    set_tenant_context(db_session, account_id)
    row = db_session.get(OutboxMessageModel, task_id)
    assert row.status == "leased"
    assert row.attempts == 1
    now = datetime.now(timezone.utc)
    row.status = "published"
    row.available_at = now - timedelta(seconds=1)
    row.lease_until = now - timedelta(seconds=1)
    db_session.commit()

    set_tenant_context(db_session, account_id)
    recovered = OutboxMessageRepository(db_session).claim_due_batch(10, 30)
    assert [message.id for message in recovered] == [task_id]
    assert recovered[0].attempts == 2


def test_charge_task_commits_completion_with_charges_and_duplicate_is_noop(
    client, auth_headers, db_session, test_engine, monkeypatch
):
    contract_id = _create_contract(client, auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=auth_headers).json()["data"]["account"]["id"])
    activation = client.put(
        f"/v1/contracts/{contract_id}",
        json={"status": "active"},
        headers=auth_headers,
    )
    assert activation.status_code == 200
    contract_uuid = UUID(contract_id)
    set_tenant_context(db_session, account_id)
    contract = db_session.get(ContractModel, contract_uuid)
    task_id = OutboxMessageRepository(db_session).create_charge_generation(
        contract.account_id, contract_uuid
    )
    _rename_committed_test_user(db_session)
    db_session.commit()

    test_sessions = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr("app.tasks.charge_tasks.SessionLocal", test_sessions)

    first_result = generate_charges_for_contract(
        str(account_id), str(contract_uuid), str(task_id)
    )
    duplicate_result = generate_charges_for_contract(
        str(account_id), str(contract_uuid), str(task_id)
    )

    assert first_result["status"] == "success"
    assert duplicate_result["status"] == "already_completed"
    set_tenant_context(db_session, account_id)
    db_session.expire_all()
    row = db_session.get(OutboxMessageModel, task_id)
    assert row.status == "completed"
    assert row.completed_at is not None
    assert (
        db_session.query(RentChargeModel)
        .filter(
            RentChargeModel.account_id == contract.account_id,
            RentChargeModel.contract_id == contract_uuid,
        )
        .count()
        > 0
    )
