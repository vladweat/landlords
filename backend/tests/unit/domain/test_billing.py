"""Unit-тесты правил SaaS-биллинга."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.billing import is_pro_period_due, is_subscription_write_blocked
from app.domain.entities import AccountEntity


def _account(**kwargs) -> AccountEntity:
    base = dict(
        id=uuid4(),
        name="A",
        owner_id=uuid4(),
        plan="pro",
        subscription_status="past_due",
        subscription_period_end=datetime.now(timezone.utc) - timedelta(days=1),
    )
    base.update(kwargs)
    return AccountEntity(**base)


class TestBillingRules:
    def test_write_blocked_after_grace(self):
        period_end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        account = _account(
            subscription_status="past_due",
            subscription_period_end=period_end,
        )
        now = period_end + timedelta(days=4)
        assert is_subscription_write_blocked(account, grace_days=3, now=now)

    def test_write_allowed_during_grace(self):
        period_end = datetime(2026, 1, 1, tzinfo=timezone.utc)
        account = _account(
            subscription_status="past_due",
            subscription_period_end=period_end,
        )
        now = period_end + timedelta(days=1)
        assert not is_subscription_write_blocked(account, grace_days=3, now=now)

    def test_write_not_blocked_when_active(self):
        account = _account(subscription_status="active")
        assert not is_subscription_write_blocked(
            account, grace_days=3, now=datetime.now(timezone.utc)
        )

    def test_pro_period_due(self):
        account = _account(
            plan="pro",
            subscription_period_end=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert is_pro_period_due(account)

    def test_free_not_due(self):
        account = _account(plan="free", subscription_period_end=None)
        assert not is_pro_period_due(account)
