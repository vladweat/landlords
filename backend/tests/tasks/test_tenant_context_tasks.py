from uuid import uuid4
from unittest.mock import Mock

from app.tasks import billing_tasks, email_tasks
from app.services import ops_heartbeat


class _Session:
    def __init__(self):
        self.commits = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        pass

    def close(self):
        pass


class _Lock:
    def __init__(self, *_args, **_kwargs):
        pass

    def try_acquire(self):
        return True

    def release(self):
        pass


def test_subscription_renewal_sets_scope_for_each_account(monkeypatch):
    account_ids = [uuid4(), uuid4()]
    session = _Session()
    resolver = Mock()
    resolver.account_ids.return_value = account_ids
    account_repo = Mock()
    account_repo.list_pro_subscriptions.return_value = []

    monkeypatch.setattr(billing_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(billing_tasks, "RedisLock", _Lock)
    monkeypatch.setattr(billing_tasks, "TenantContextRepository", lambda _session: resolver)
    set_context = Mock()
    monkeypatch.setattr(billing_tasks, "set_tenant_context", set_context)
    monkeypatch.setattr(billing_tasks, "AccountRepository", lambda _session: account_repo)
    monkeypatch.setattr(ops_heartbeat, "mark_beat_ok", lambda: None)

    result = billing_tasks.process_subscription_renewals()

    assert result == {
        "status": "success",
        "renewed": 0,
        "past_due": 0,
        "downgraded": 0,
        "skipped": 0,
    }
    assert [call.args[1] for call in set_context.call_args_list] == account_ids
    assert session.commits == 2


def test_daily_reminders_process_each_account_under_its_scope(monkeypatch):
    account_ids = [uuid4(), uuid4()]
    session = _Session()
    resolver = Mock()
    resolver.account_ids.return_value = account_ids
    service = Mock()
    service.send_daily_reminders.return_value = {
        "sent": 0,
        "skipped": 0,
        "errors": 0,
        "retryable_errors": 0,
    }

    monkeypatch.setattr(email_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(email_tasks, "RedisLock", _Lock)
    monkeypatch.setattr(email_tasks, "TenantContextRepository", lambda _session: resolver)
    set_context = Mock()
    monkeypatch.setattr(email_tasks, "set_tenant_context", set_context)
    monkeypatch.setattr(email_tasks, "ReminderEmailService", lambda **_kwargs: service)
    monkeypatch.setattr(ops_heartbeat, "mark_beat_ok", lambda: None)

    result = email_tasks.send_daily_reminder_emails()

    assert result == {
        "status": "success",
        "sent": 0,
        "skipped": 0,
        "errors": 0,
        "retryable_errors": 0,
    }
    assert [call.args[1] for call in set_context.call_args_list] == account_ids
    assert [call.args[0] for call in service.send_daily_reminders.call_args_list] == account_ids
    assert session.commits == 2
