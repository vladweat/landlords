"""Человекочитаемые подписи для событий договора (UI на русском)."""

from datetime import date
from decimal import Decimal

CONTRACT_STATUS_LABELS: dict[str, str] = {
    "draft": "Черновик",
    "active": "Активен",
    "ended": "Завершён",
    "overdue": "Просрочен",
    "terminated": "Расторгнут",
}

REMINDER_TYPE_LABELS: dict[str, str] = {
    "first": "первое",
    "second": "второе",
    "third": "третье",
}

PAYMENT_METHOD_LABELS: dict[str, str] = {
    "transfer": "перевод",
    "cash": "наличные",
    "card": "карта",
    "bank": "банк",
}


def status_label(status: str) -> str:
    return CONTRACT_STATUS_LABELS.get(status, status)


def reminder_type_label(reminder_type: str) -> str:
    return REMINDER_TYPE_LABELS.get(reminder_type, reminder_type)


def payment_method_label(method: str) -> str:
    return PAYMENT_METHOD_LABELS.get(method, method)


def format_money(amount: Decimal, currency: str) -> str:
    """Формат суммы для заголовков событий."""
    quantized = amount.quantize(Decimal("0.01"))
    if quantized == quantized.to_integral_value():
        text = f"{int(quantized):,}".replace(",", "\u00a0")
    else:
        text = f"{quantized:,.2f}".replace(",", "\u00a0")
    return f"{text} {currency}"


def format_date_ru(value: date) -> str:
    return value.strftime("%d.%m.%Y")
