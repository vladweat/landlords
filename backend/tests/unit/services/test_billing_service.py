"""Unit-тесты BillingService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.domain.entities import AccountEntity
from app.services.billing_service import BillingService
from app.services.yookassa_client import YooKassaPaymentResult


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def account(account_id):
    return AccountEntity(
        id=account_id,
        name="Test Co",
        owner_id=uuid4(),
        plan="free",
        subscription_status="none",
    )


@pytest.fixture
def yookassa():
    client = Mock()
    client.enabled = True
    return client


@pytest.fixture
def service(account, yookassa):
    repo = Mock()
    repo.get_by_id.return_value = account
    repo.update.side_effect = lambda e: e
    repo.list_pro_subscriptions.return_value = []
    return BillingService(repo, yookassa), repo, yookassa


def _payment(**kwargs) -> YooKassaPaymentResult:
    base = dict(
        id="pay_1",
        status="succeeded",
        paid=True,
        amount_value="990.00",
        confirmation_url="https://yookassa.test/confirm",
        payment_method_id="pm_1",
        metadata={},
        test=True,
    )
    base.update(kwargs)
    return YooKassaPaymentResult(**base)


class TestBillingService:
    def test_checkout_returns_url(self, service, account_id, yookassa):
        svc, *_ = service
        yookassa.create_checkout_payment.return_value = _payment()
        data = svc.create_checkout(account_id)
        assert data["confirmation_url"].startswith("https://")
        assert data["payment_id"] == "pay_1"

    def test_checkout_disabled(self, service, account_id, yookassa):
        svc, *_ = service
        yookassa.enabled = False
        with pytest.raises(ValidationError, match="не настроена"):
            svc.create_checkout(account_id)

    def test_webhook_applies_pro(self, service, account, account_id, yookassa):
        svc, repo, _ = service
        yookassa.find_payment.return_value = _payment(
            metadata={"account_id": str(account_id), "plan": "pro"}
        )
        result = svc.handle_webhook({"object": {"id": "pay_1"}})
        assert result["status"] == "applied"
        assert account.plan == "pro"
        assert account.subscription_status == "active"
        assert account.yookassa_payment_method_id == "pm_1"
        assert account.subscription_period_end is not None
        repo.update.assert_called()

    def test_confirm_payment_same_as_webhook(self, service, account, account_id, yookassa):
        svc, *_ = service
        yookassa.find_payment.return_value = _payment(
            metadata={"account_id": str(account_id), "plan": "pro"}
        )
        result = svc.confirm_payment(account_id, "pay_1")
        assert result["status"] == "applied"
        assert account.plan == "pro"

    def test_confirm_rejects_foreign_account(self, service, account_id, yookassa):
        svc, *_ = service
        yookassa.find_payment.return_value = _payment(
            metadata={"account_id": str(uuid4()), "plan": "pro"}
        )
        with pytest.raises(ValidationError, match="другому аккаунту"):
            svc.confirm_payment(account_id, "pay_1")

    def test_webhook_idempotent(self, service, account, account_id, yookassa):
        svc, repo, _ = service
        account.yookassa_last_payment_id = "pay_1"
        yookassa.find_payment.return_value = _payment(
            metadata={"account_id": str(account_id)}
        )
        result = svc.handle_webhook({"object": {"id": "pay_1"}})
        assert result["status"] == "ignored"
        repo.update.assert_not_called()

    def test_cancel_immediate_when_period_ended(self, service, account):
        svc, *_ = service
        account.plan = "pro"
        account.subscription_status = "active"
        account.yookassa_payment_method_id = "pm_1"
        account.subscription_period_end = datetime.now(timezone.utc) - timedelta(days=1)
        updated = svc.cancel_subscription(account.id)
        assert updated.plan == "free"
        assert updated.subscription_status == "none"
        assert updated.yookassa_payment_method_id is None

    def test_cancel_keeps_period(self, service, account):
        svc, *_ = service
        account.plan = "pro"
        account.subscription_status = "active"
        account.yookassa_payment_method_id = "pm_1"
        end = datetime.now(timezone.utc) + timedelta(days=10)
        account.subscription_period_end = end
        updated = svc.cancel_subscription(account.id)
        assert updated.plan == "pro"
        assert updated.subscription_status == "canceled"
        assert updated.yookassa_payment_method_id is None
        assert updated.subscription_period_end == end

    def test_renew_success(self, service, account, yookassa):
        svc, repo, _ = service
        account.plan = "pro"
        account.subscription_status = "active"
        account.yookassa_payment_method_id = "pm_1"
        account.subscription_period_end = datetime.now(timezone.utc) - timedelta(hours=1)
        repo.list_pro_subscriptions.return_value = [account]
        yookassa.create_recurring_payment.return_value = _payment(id="pay_renew")
        stats = svc.process_renewals()
        assert stats["renewed"] == 1
        assert account.subscription_status == "active"
        assert account.yookassa_last_payment_id == "pay_renew"

    def test_renew_fail_then_downgrade_after_grace(self, service, account, yookassa):
        svc, repo, _ = service
        account.plan = "pro"
        account.subscription_status = "active"
        account.yookassa_payment_method_id = "pm_1"
        account.subscription_period_end = datetime.now(timezone.utc) - timedelta(days=5)
        repo.list_pro_subscriptions.return_value = [account]
        yookassa.create_recurring_payment.return_value = _payment(
            id="pay_fail", status="canceled", paid=False
        )
        stats = svc.process_renewals()
        assert stats["past_due"] == 1
        assert stats["downgraded"] == 1
        assert account.plan == "free"

    def test_canceled_downgrades_at_period_end(self, service, account, yookassa):
        svc, repo, _ = service
        account.plan = "pro"
        account.subscription_status = "canceled"
        account.yookassa_payment_method_id = None
        account.subscription_period_end = datetime.now(timezone.utc) - timedelta(hours=1)
        repo.list_pro_subscriptions.return_value = [account]
        stats = svc.process_renewals()
        assert stats["downgraded"] == 1
        assert account.plan == "free"
