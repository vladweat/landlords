from unittest.mock import Mock
from uuid import uuid4

from app.db.repositories.outbox_message_repo import OutboxMessageRepository


def test_create_charge_generation_flushes_allowlisted_row_without_commit():
    session = Mock()
    repository = OutboxMessageRepository(session)
    account_id = uuid4()
    contract_id = uuid4()

    task_id = repository.create_charge_generation(account_id, contract_id)

    row = session.add.call_args.args[0]
    assert row.id == task_id
    assert row.account_id == account_id
    assert row.contract_id == contract_id
    assert row.task_name == "app.tasks.charge_tasks.generate_charges_for_contract"
    assert row.payload_version == 1
    assert row.status == "pending"
    session.flush.assert_called_once()
    session.commit.assert_not_called()
