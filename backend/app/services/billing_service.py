"""SaaS-биллинг через ЮKassa: checkout, webhook, cancel, renew."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable
from uuid import UUID, uuid5

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.db.tenant_context import set_tenant_context
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
        commit: Callable[[], None] | None = None,
        session: Session | None = None,
    ) -> None:
        self.account_repo = account_repo
        self.yookassa = yookassa or YooKassaClient()
        self.commit = commit or (lambda: None)
        self.session = session

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

        if self.session is not None:
            set_tenant_context(self.session, account_id)
        account = self._require_account_for_update(account_id)
        if account is None:
            raise NotFoundError("Account not found")
        if account.yookassa_last_payment_id == payment.id:
            return {"status": "ignored", "reason": "duplicate"}

        if payment.status == "succeeded" and payment.paid:
            if payment.metadata.get("renew") == "1" and payment.metadata.get(
                "billing_period_end"
            ):
                period_end = self._parse_period_end(payment.metadata["billing_period_end"])
                if (
                    account.subscription_period_end is None
                    or self._as_utc(account.subscription_period_end) != period_end
                ):
                    return {"status": "ignored", "reason": "period_already_advanced"}
                self._apply_renewal_payment(account, payment, period_end)
            else:
                self._apply_successful_payment(account, payment)
            return {"status": "applied", "account_id": str(account_id)}

        if payment.status in ("canceled", "cancelled"):
            return {"status": "ignored", "reason": payment.status}

        return {"status": "ignored", "reason": payment.status}

    def cancel_subscription(self, account_id: UUID) -> AccountEntity:
        """Отменить автоплатежи; Free сразу или в конце оплаченного периода."""
        account = self._require_account_for_update(account_id)
        if account is None:
            raise NotFoundError("Account not found")
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

    def process_renewals(
        self, *, now: datetime | None = None, account_id: UUID | None = None
    ) -> dict:
        """Продлить или отключить Pro с истёкшим периодом (Celery beat)."""
        moment = now or datetime.now(timezone.utc)
        renewed = 0
        past_due = 0
        downgraded = 0
        skipped = 0

        for listed_account in self.account_repo.list_pro_subscriptions():
            if account_id is not None and listed_account.id != account_id:
                continue
            account = self._require_account_for_update(listed_account.id)
            if account is None or account.plan != PlanId.PRO.value:
                continue
            if not is_pro_period_due(account, now=moment):
                skipped += 1
                self.commit()
                continue

            # Отмена: в конце оплаченного периода сразу на Free
            if account.subscription_status == SubscriptionStatus.CANCELED.value:
                self._downgrade_to_free(account)
                self.commit()
                downgraded += 1
                continue

            if not account.yookassa_payment_method_id:
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    self.commit()
                    downgraded += 1
                elif account.subscription_status != SubscriptionStatus.PAST_DUE.value:
                    account.subscription_status = SubscriptionStatus.PAST_DUE.value
                    self.account_repo.update(account)
                    self.commit()
                    past_due += 1
                else:
                    self.commit()
                    skipped += 1
                continue

            if not self.yookassa.enabled:
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                self.account_repo.update(account)
                self.commit()
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    self.commit()
                    downgraded += 1
                continue

            period_end = self._as_utc(account.subscription_period_end)
            idempotence_key = f"renew-{uuid5(account.id, period_end.isoformat())}"
            if (
                account.yookassa_renewal_period_end is None
                or self._as_utc(account.yookassa_renewal_period_end) != period_end
            ):
                account.yookassa_renewal_period_end = period_end
                account.yookassa_renewal_started_at = moment
                account.yookassa_renewal_idempotence_key = idempotence_key
                account.yookassa_renewal_payment_id = None
                account.yookassa_renewal_status = "pending"
                self.account_repo.update(account)
                # Commit the stable period identity and release the row lock before HTTP.
                self.commit()
            elif account.yookassa_renewal_started_at is None:
                account.yookassa_renewal_started_at = moment
                self.account_repo.update(account)
                self.commit()

            idempotence_key = account.yookassa_renewal_idempotence_key or idempotence_key
            # Existing attempts also release their row lock before provider I/O.
            self.commit()
            try:
                if account.yookassa_renewal_payment_id:
                    payment = self.yookassa.find_payment(
                        account.yookassa_renewal_payment_id
                    )
                else:
                    payment_id = self.yookassa.find_renewal_payment_id(
                        account_id=str(account.id),
                        billing_period_end=period_end.isoformat(),
                        created_after=account.yookassa_renewal_started_at or moment,
                    )
                    if payment_id:
                        payment = self.yookassa.find_payment(payment_id)
                    else:
                        payment = self.yookassa.create_recurring_payment(
                            amount_rub=Decimal(settings.BILLING_PRO_PRICE_RUB),
                            description=f"Landlords Pro (renew) — {account.name}",
                            payment_method_id=account.yookassa_payment_method_id,
                            metadata={
                                "account_id": str(account.id),
                                "plan": PlanId.PRO.value,
                                "renew": "1",
                                "billing_period_end": period_end.isoformat(),
                            },
                            idempotence_key=idempotence_key,
                        )
            except Exception:
                # Reconciliation must succeed before any retry can create a payment.
                account = self._require_account_for_update(listed_account.id)
                if account is None or account.subscription_period_end is None:
                    continue
                if self._as_utc(account.subscription_period_end) != period_end:
                    continue
                account.yookassa_renewal_status = "unknown"
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                self.account_repo.update(account)
                self.commit()
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    self.commit()
                    downgraded += 1
                continue

            # Reacquire and refresh after HTTP. A webhook may have finalized the
            # same period while the request was in flight.
            account = self._require_account_for_update(listed_account.id)
            if account is None or account.subscription_period_end is None:
                self.commit()
                continue
            if self._as_utc(account.subscription_period_end) != period_end:
                self.commit()
                continue

            account.yookassa_renewal_payment_id = payment.id
            account.yookassa_renewal_status = payment.status
            if payment.status == "succeeded" and payment.paid:
                self._apply_renewal_payment(account, payment, period_end)
                self.commit()
                renewed += 1
            else:
                account.subscription_status = SubscriptionStatus.PAST_DUE.value
                self.account_repo.update(account)
                self.commit()
                past_due += 1
                if self._grace_expired(account, moment):
                    self._downgrade_to_free(account)
                    self.commit()
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

    def _apply_renewal_payment(
        self, account: AccountEntity, payment: YooKassaPaymentResult, period_end: datetime
    ) -> AccountEntity:
        """Применить списание только к исходному неоплаченному периоду."""
        if account.yookassa_last_payment_id == payment.id:
            return account
        if account.subscription_period_end is None:
            return account
        if self._as_utc(account.subscription_period_end) != self._as_utc(period_end):
            return account
        self._apply_successful_payment(account, payment, from_period_end=True)
        account.yookassa_renewal_period_end = period_end
        account.yookassa_renewal_payment_id = payment.id
        account.yookassa_renewal_status = "succeeded"
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

    def _require_account_for_update(self, account_id: UUID) -> AccountEntity | None:
        return self.account_repo.get_by_id_for_update(account_id)

    @staticmethod
    def _parse_period_end(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
