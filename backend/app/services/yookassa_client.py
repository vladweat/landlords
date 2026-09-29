"""Тонкая обёртка над SDK ЮKassa."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, ValidationError


@dataclass(frozen=True)
class YooKassaPaymentResult:
    """Нормализованный ответ по платежу."""

    id: str
    status: str
    paid: bool
    amount_value: str
    confirmation_url: str | None
    payment_method_id: str | None
    metadata: dict[str, str]
    test: bool


class YooKassaClient:
    """Создание и получение платежей ЮKassa."""

    def __init__(
        self,
        shop_id: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        self.shop_id = shop_id if shop_id is not None else settings.YOOKASSA_SHOP_ID
        self.secret_key = (
            secret_key if secret_key is not None else settings.YOOKASSA_SECRET_KEY
        )

    @property
    def enabled(self) -> bool:
        return bool(self.shop_id and self.secret_key)

    def _configure(self) -> None:
        if not self.enabled:
            raise ValidationError(
                "Оплата не настроена: задайте YOOKASSA_SHOP_ID и YOOKASSA_SECRET_KEY"
            )
        try:
            from yookassa import Configuration
        except ImportError as exc:
            raise ServiceUnavailableError(
                "Пакет yookassa не установлен"
            ) from exc
        Configuration.account_id = self.shop_id
        Configuration.secret_key = self.secret_key

    def create_checkout_payment(
        self,
        *,
        amount_rub: Decimal,
        description: str,
        return_url: str,
        metadata: dict[str, str],
        idempotence_key: str | None = None,
    ) -> YooKassaPaymentResult:
        """Платёж с редиректом и сохранением способа оплаты."""
        self._configure()
        from yookassa import Payment

        payload: dict[str, Any] = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": description,
            "metadata": metadata,
            "save_payment_method": True,
        }
        try:
            payment = Payment.create(payload, idempotence_key or str(uuid4()))
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Не удалось создать платёж ЮKassa: {exc}"
            ) from exc
        return self._to_result(payment)

    def create_recurring_payment(
        self,
        *,
        amount_rub: Decimal,
        description: str,
        payment_method_id: str,
        metadata: dict[str, str],
        idempotence_key: str | None = None,
    ) -> YooKassaPaymentResult:
        """Автоплатёж по сохранённому способу оплаты."""
        self._configure()
        from yookassa import Payment

        payload: dict[str, Any] = {
            "amount": {"value": f"{amount_rub:.2f}", "currency": "RUB"},
            "capture": True,
            "description": description,
            "metadata": metadata,
            "payment_method_id": payment_method_id,
        }
        try:
            payment = Payment.create(payload, idempotence_key or str(uuid4()))
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Не удалось создать автоплатёж ЮKassa: {exc}"
            ) from exc
        return self._to_result(payment)

    def find_payment(self, payment_id: str) -> YooKassaPaymentResult:
        """Получить актуальный статус платежа из API."""
        self._configure()
        from yookassa import Payment

        try:
            payment = Payment.find_one(payment_id)
        except Exception as exc:
            raise ServiceUnavailableError(
                f"Не удалось получить платёж ЮKassa: {exc}"
            ) from exc
        return self._to_result(payment)

    @staticmethod
    def _to_result(payment: Any) -> YooKassaPaymentResult:
        confirmation_url = None
        confirmation = getattr(payment, "confirmation", None)
        if confirmation is not None:
            confirmation_url = getattr(confirmation, "confirmation_url", None)

        payment_method_id = None
        payment_method = getattr(payment, "payment_method", None)
        if payment_method is not None:
            payment_method_id = getattr(payment_method, "id", None)
            saved = getattr(payment_method, "saved", None)
            if saved is False:
                payment_method_id = payment_method_id  # всё равно сохраняем id при наличии

        raw_meta = getattr(payment, "metadata", None) or {}
        metadata = {str(k): str(v) for k, v in dict(raw_meta).items()}

        amount = getattr(payment, "amount", None)
        amount_value = "0.00"
        if amount is not None:
            amount_value = str(getattr(amount, "value", "0.00"))

        return YooKassaPaymentResult(
            id=str(payment.id),
            status=str(payment.status),
            paid=bool(getattr(payment, "paid", False)),
            amount_value=amount_value,
            confirmation_url=confirmation_url,
            payment_method_id=payment_method_id,
            metadata=metadata,
            test=bool(getattr(payment, "test", False)),
        )
