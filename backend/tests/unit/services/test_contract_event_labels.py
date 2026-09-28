"""Unit-тесты подписей событий договора."""

from datetime import date
from decimal import Decimal

from app.services.contract_event_labels import (
    format_date_ru,
    format_money,
    reminder_type_label,
    status_label,
)


def test_status_labels_russian():
    assert status_label("draft") == "Черновик"
    assert status_label("active") == "Активен"
    assert status_label("unknown") == "unknown"


def test_reminder_type_labels_russian():
    assert reminder_type_label("first") == "первое"
    assert reminder_type_label("second") == "второе"
    assert reminder_type_label("third") == "третье"


def test_format_money_and_date():
    assert format_money(Decimal("50000"), "RUB") == "50\u00a0000 RUB"
    assert format_money(Decimal("1500.50"), "RUB") == "1\u00a0500.50 RUB"
    assert format_date_ru(date(2026, 3, 15)) == "15.03.2026"
