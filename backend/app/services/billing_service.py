"""SaaS-биллинг через ЮKassa: checkout, webhook, cancel, renew."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.billing import is_pro_period_due
from app.domain.entities import AccountEntity
from app.domain.interfaces import IAccountRepository
from app.domain.plans import (
    DEFAULT_PLAN,
    PlanId,
    SubscriptionStatus,
)
from app.services.yookassa_client import YooKassaClient, YooKassaPaymentResult


class BillingService:
    """Оплата тарифа Pro и жизненный цикл подписки."""

    def __init__(
        self,
        account_repo: IAccountRepository,
        yookassa: YooKassaClient | None = None,
    ) -> None:
        self.account_repo = account_repo
        self.yookassa = yookassa or YooKassaClient()

    def create_checkout(self, account_id: UUID) -> dict:
        """Создать платёж Pro и вернуть confirmation_url."""
        if not self.yookassa.enabled:
            raise ValidationError(
                "Оплата не настроена: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
            )
        account = self._require_account(account_id)
        if account.plan == PlanId.PRO.value and account.subscription_status == (
            SubscriptionStatus.ACTIVE.value
        ):
            raise ValidationError("Тариф Pro уже активен")

        amount = Decimal(settings.BILLING_PRO_PRICE_RUB)
        payment = self.yookassa.create_checkout_payment(
            amount_rub=amount,
            description=f"Landlords Pro — {account.name}",
            return_url=settings.yookassa_return_url,
            metadata={
                "account_id": str(account.id),
                "plan": PlanId.PRO.value,
            },
        )
        if not payment.confirmation_url:
            raise ValidationError("ЮKassa не вернула ссылку на оплату")
        return {
            "confirmation_url": payment.confirmation_url,
            "payment_id": payment.id,
        }

    def confirm_payment(self, account_id: UUID, payment_id: str) -> dict:
        """Подтвердить оплату после return_url (без webhook / ngrok)."""
        if not self.yookassa.enabled:
            raise ValidationError(
                "Оплата не настроена: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
            )
        if not payment_id or not payment_id.strip():
            raise ValidationError("Не указан payment_id")
        return self._apply_payment_id(payment_id.strip(), expected_account_id=account_id)

    def handle_webhook(self, payload: dict) -> dict:
        """Обработать HTTP-уведомление ЮKassa (истина — из API find)."""
        obj = payload.get("object") or {}
        payment_id = obj.get("id") if isinstance(obj, dict) else None
        if not payment_id:
            raise ValidationError("В уведомлении нет id платежа")
        return self._apply_payment_id(str(payment_id), expected_account_id=None)

    def _apply_payment_id(
        self,
        payment_id: str,
        *,
        expected_account_id: UUID | None,
    ) -> dict:
        """Найти платёж в ЮKassa и применить к аккаунту."""
        payment = self.yookassa.find_payment(payment_id)
        account_id_raw = payment.metadata.get("account_id")
        if not account_id_raw:
            raise ValidationError("В платеже нет metadata.account_id")
        try:
            account_id = UUID(account_id_raw)
        except ValueError as exc:
            raise ValidationError("Некорректный account_id в metadata") from exc

        if expected_account_id is not None and account_id != expected_account_id:
            raise ValidationError("Платёж принадлежит другому аккаунту")

        account = self._require_account(account_id)
        if account.yookassa_last_payment_id == payment.id:
            return {"status": "ignored", "reason": "duplicate"}

        if payment.status == "succeeded" and payment.paid:
            self._apply_successful_payment(account, payment)
            return {"status": "applied", "account_id": str(account_id)}

        if payment.status in ("canceled", "cancelled"):
            return {"status": "ignored", "reason": payment.status}

        return {"status": "ignored", "reason": payment.status}

    def cancel_subscription(self, account_id: UUID) -> AccountEntity:
        """Отменить автоплатежи; Free сразу или в конце оплаченного периода."""
        account = self._require_account(account_id)
        if account.plan != PlanId.PRO.value:
            raise ValidationError("Нет активной подписки Pro для отмены")

        now = datetime.now(timezone.utc)
        account.yookassa_payment_method_id = None
        account.subscription_status = SubscriptionStatus.CANCELED.value

        period_end = account.subscription_period_end
        if period_end is None or self._as_utc(period_end) <= now:
            account.plan = DEFAULT_PLAN
            account.subscription_status = SubscriptionStatus.NONE.value
            account.subscription_period_end = None
        return self.account_repo.update(account)

    def process_renewals(self, *, now: datetime | None = None) -> dict:
        """Продлить или отключить Pro с истёкшим периодом (Celery beat)."""
        moment = now or datetime.now(timezone.utc)
        renewed = 0
        past_due = 0
        downgraded = 0
        skipped = 0

        for account in self.account_repo.list_pro_subscriptions():
            if not is_pro_period_due(account, now=moment):
                skipped += 1
                continue

            # Отмена: в конце оплаченного периода сразу на Free
            if account.subscription_status == SubscriptionStatus.CANCELED.value:
                self._downgrade_to_free(account)
                downgraded += 1
                continue

            if not account.yookassa_payment_method_id:
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    downgraded += 1
                elif account.subscription_status != SubscriptionStatus.PAST_DUE.value:
                    account.subscription_status = SubscriptionStatus.PAST_DUE.value
                    self.account_repo.update(account)
                    past_due += 1
                else:
                    skipped += 1
                continue

            if not self.yookassa.enabled:
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                self.account_repo.update(account)
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    downgraded += 1
                continue

            try:
                payment = self.yookassa.create_recurring_payment(
                    amount_rub=Decimal(settings.BILLING_PRO_PRICE_RUB),
                    description=f"Landlords Pro (renew) — {account.name}",
                    payment_method_id=account.yookassa_payment_method_id,
                    metadata={
                        "account_id": str(account.id),
                        "plan": PlanId.PRO.value,
                        "renew": "1",
                    },
                    idempotence_key=f"renew-{account.id}-{moment.date().isoformat()}",
                )
            except Exception:
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                self.account_repo.update(account)
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    downgraded += 1
                continue

            if payment.status == "succeeded" and payment.paid:
                self._apply_successful_payment(account, payment, from_period_end=True)
                renewed += 1
            else:
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                account.yookassa_last_payment_id = payment.id
                self.account_repo.update(account)
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    downgraded += 1

        return {
            "renewed": renewed,
            "past_due": past_due,
            "downgraded": downgraded,
            "skipped": skipped,
        }

    def _apply_successful_payment(
        self,
        account: AccountEntity,
        payment: YooKassaPaymentResult,
        *,
        from_period_end: bool = False,
    ) -> AccountEntity:
        now = datetime.now(timezone.utc)
        base = now
        if from_period_end and account.subscription_period_end:
            base = max(self._as_utc(account.subscription_period_end), now)

        account.plan = PlanId.PRO.value
        account.subscription_status = SubscriptionStatus.ACTIVE.value
        account.subscription_period_end = base + timedelta(days=30)
        account.yookassa_last_payment_id = payment.id
        if payment.payment_method_id:
            account.yookassa_payment_method_id = payment.payment_method_id
        return self.account_repo.update(account)

    def _downgrade_to_free(self, account: AccountEntity) -> AccountEntity:
        account.plan = DEFAULT_PLAN
        account.subscription_status = SubscriptionStatus.NONE.value
        account.subscription_period_end = None
        account.yookassa_payment_method_id = None
        return self.account_repo.update(account)

    def _grace_expired(self, account: AccountEntity, now: datetime) -> bool:
        if account.subscription_period_end is None:
            return True
        grace_end = self._as_utc(account.subscription_period_end) + timedelta(
            days=settings.BILLING_GRACE_DAYS
        )
        return now > grace_end

    def _require_account(self, account_id: UUID) -> AccountEntity:
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        return account

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
