"""Unit-тесты BillingService."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.domain.entities import AccountEntity
from app.services.billing_service import BillingService
from app.services.yookassa_client import YooKassaClient, YooKassaPaymentResult


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
    client.find_renewal_payment_id.return_value = None
    return client


@pytest.fixture
def service(account, yookassa):
    repo = Mock()
    repo.get_by_id.return_value = account
    repo.get_by_id_for_update.return_value = account
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

    def test_renew_reconciliation_failure_does_not_create_payment(
        self, service, account, yookassa
    ):
        svc, repo, _ = service
        account.plan = "pro"
        account.subscription_status = "active"
        account.yookassa_payment_method_id = "pm_1"
        account.subscription_period_end = datetime.now(timezone.utc) - timedelta(hours=1)
        repo.list_pro_subscriptions.return_value = [account]
        yookassa.find_renewal_payment_id.side_effect = RuntimeError("provider unavailable")
        yookassa.create_recurring_payment.return_value = _payment(id="pay_renew")
        stats = svc.process_renewals()
        assert stats["renewed"] == 0
        assert stats["past_due"] == 1
        assert account.yookassa_renewal_status == "unknown"
        yookassa.create_recurring_payment.assert_not_called()

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


class TestYooKassaRenewalReconciliation:
    def test_finds_matching_payment_across_pages(self):
        first_page = SimpleNamespace(
            items=[SimpleNamespace(id="unrelated", metadata={"account_id": "other"})],
            next_cursor="next-page",
        )
        second_page = SimpleNamespace(
            items=[
                SimpleNamespace(
                    id="renewal-payment",
                    metadata={
                        "account_id": "account-1",
                        "renew": "1",
                        "billing_period_end": "2026-10-20T00:00:00+00:00",
                    },
                )
            ],
            next_cursor=None,
        )
        client = YooKassaClient("shop-test", "secret-test")
        with patch("yookassa.Payment.list", side_effect=[first_page, second_page]) as listing:
            payment_id = client.find_renewal_payment_id(
                account_id="account-1",
                billing_period_end="2026-10-20T00:00:00+00:00",
                created_after=datetime(2026, 10, 20, tzinfo=timezone.utc),
            )

        assert payment_id == "renewal-payment"
        assert listing.call_count == 2
        assert listing.call_args.args[0]["cursor"] == "next-page"

    def test_rejects_ambiguous_period_match(self):
        matching_metadata = {
            "account_id": "account-1",
            "renew": "1",
            "billing_period_end": "2026-10-20T00:00:00+00:00",
        }
        page = SimpleNamespace(
            items=[
                SimpleNamespace(id="renewal-1", metadata=matching_metadata),
                SimpleNamespace(id="renewal-2", metadata=matching_metadata),
            ],
            next_cursor=None,
        )
        client = YooKassaClient("shop-test", "secret-test")
        with patch("yookassa.Payment.list", return_value=page):
            with pytest.raises(ServiceUnavailableError, match="несколько автоплатежей"):
                client.find_renewal_payment_id(
                    account_id="account-1",
                    billing_period_end="2026-10-20T00:00:00+00:00",
                    created_after=datetime(2026, 10, 20, tzinfo=timezone.utc),
                )
