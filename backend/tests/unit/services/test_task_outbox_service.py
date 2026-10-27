from unittest.mock import Mock
from uuid import uuid4

from app.services.task_outbox_service import TaskOutboxService


def test_enqueue_charge_generation_returns_repository_task_id():
    account_id = uuid4()
    contract_id = uuid4()
    task_id = uuid4()
    repository = Mock()
    repository.create_charge_generation.return_value = task_id

    result = TaskOutboxService(repository).enqueue_charge_generation(
        account_id, contract_id
    )

    assert result == task_id
    repository.create_charge_generation.assert_called_once_with(account_id, contract_id)
