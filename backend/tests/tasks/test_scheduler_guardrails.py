import pytest

from app.tasks import billing_tasks, charge_tasks, email_tasks, lock as lock_module


@pytest.mark.parametrize(
    ("task", "module", "lock_name"),
    [
        (charge_tasks.update_overdue_charges, charge_tasks, "update_overdue_charges"),
        (
            email_tasks.send_daily_reminder_emails,
            email_tasks,
            "send_daily_reminder_emails",
        ),
        (
            billing_tasks.process_subscription_renewals,
            billing_tasks,
            "process_subscription_renewals",
        ),
    ],
)
def test_scheduled_task_lock_ttl_is_nine_hundred_and_exceeds_task_limit(
    task, module, lock_name, monkeypatch
):
    ttl_seconds = getattr(lock_module, "SCHEDULED_TASK_LOCK_TTL_SECONDS", None)
    assert ttl_seconds == 900
    assert task.time_limit <= 600

    observed = {}

    class UnavailableLock:
        def __init__(self, name, ttl):
            observed["name"] = name
            observed["ttl"] = ttl

        def try_acquire(self):
            return False

    monkeypatch.setattr(module, "RedisLock", UnavailableLock)

    assert task.run() == {"status": "skipped", "reason": "lock_not_acquired"}
    assert observed == {"name": lock_name, "ttl": ttl_seconds}
