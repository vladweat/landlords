from datetime import datetime, timedelta, timezone
from dataclasses import replace
from unittest.mock import Mock
from uuid import UUID, uuid4

from app.domain.entities import OutboxMessageEntity
from app.services.outbox_relay import OutboxRelay


def _message(attempts: int = 1) -> OutboxMessageEntity:
    return OutboxMessageEntity(
        id=uuid4(),
        account_id=uuid4(),
        contract_id=uuid4(),
        task_name="app.tasks.charge_tasks.generate_charges_for_contract",
        attempts=attempts,
        lease_token=uuid4(),
        lease_until=datetime.now(timezone.utc) + timedelta(minutes=5),
    )


def test_dispatch_publishes_stable_task_id_after_claim_commit():
    message = _message()
    sessions = []
    repository = Mock()
    repository.claim_due_batch.return_value = [message]
    repository.backlog_snapshot.return_value = (0, 0.0, 0)

    class Session:
        committed = False

        def execute(self, statement, params=None):
            if "app_outbox_account_ids" in str(statement):
                return [Mock(account_id=message.account_id)]
            if "app_account_ids" in str(statement):
                return [Mock(account_id=message.account_id)]
            return None

        def commit(self):
            self.committed = True

        def rollback(self):
            pass

        def close(self):
            pass

    def session_factory():
        session = Session()
        sessions.append(session)
        return session

    publisher = Mock()

    def send_task(*args, **kwargs):
        assert sessions[0].committed
        return Mock()

    publisher.send_task.side_effect = send_task
    relay = OutboxRelay(
        session_factory=session_factory,
        publisher=publisher,
        repository_factory=lambda session: repository,
    )

    summary = relay.dispatch_once()

    assert summary.claimed == 1
    assert summary.published == 1
    publisher.send_task.assert_called_once_with(
        message.task_name,
        args=[str(message.account_id), str(message.contract_id), str(message.id)],
        task_id=str(message.id),
    )
    repository.mark_published.assert_called_once_with(
        message.id, message.account_id, message.lease_token
    )


def test_dispatch_failure_schedules_retry_and_stores_only_error_type():
    message = _message(attempts=2)
    repository = Mock()
    repository.claim_due_batch.return_value = [message]
    repository.backlog_snapshot.return_value = (0, 0.0, 0)
    repository.mark_dispatch_failure.return_value = False
    publisher = Mock()
    publisher.send_task.side_effect = ConnectionError("redis password=secret")
    class Session:
        def execute(self, statement, params=None):
            if "app_outbox_account_ids" in str(statement):
                return [Mock(account_id=message.account_id)]
            if "app_account_ids" in str(statement):
                return [Mock(account_id=message.account_id)]
            return None

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    session_factory = Mock(side_effect=Session)

    summary = OutboxRelay(
        session_factory=session_factory,
        publisher=publisher,
        repository_factory=lambda session: repository,
        jitter_ratio=0,
    ).dispatch_once()

    assert summary.retried == 1
    args = repository.mark_dispatch_failure.call_args.args
    assert args[0:3] == (message.id, message.account_id, message.lease_token)
    assert args[3] > datetime.now(timezone.utc)
    assert args[4] == "ConnectionError"


def test_dispatch_claims_messages_under_each_account_context():
    account_a, account_b = uuid4(), uuid4()
    message_a = replace(_message(), account_id=account_a)
    message_b = replace(_message(), account_id=account_b)
    messages_by_account = {account_a: message_a, account_b: message_b}
    claim_scopes = []

    class Session:
        account_id = None

        def execute(self, statement, params=None):
            if "app_outbox_account_ids" in str(statement):
                return [Mock(account_id=account_a), Mock(account_id=account_b)]
            if "app_account_ids" in str(statement):
                return [Mock(account_id=account_a), Mock(account_id=account_b)]
            if "set_config" in str(statement):
                self.account_id = UUID(params["account_id"])
            return None

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    def repository_factory(session):
        class Repository:
            def claim_due_batch(self, _batch_size, _lease_seconds):
                claim_scopes.append(session.account_id)
                message = messages_by_account.get(session.account_id)
                return [message] if message else []

            def mark_published(self, *_args):
                return True

            def backlog_snapshot(self):
                return (0, 0.0, 0)

        return Repository()

    summary = OutboxRelay(
        session_factory=Session,
        publisher=Mock(),
        repository_factory=repository_factory,
    ).dispatch_once()

    assert claim_scopes == [account_a, account_b]
    assert summary.claimed == 2
    assert summary.published == 2
