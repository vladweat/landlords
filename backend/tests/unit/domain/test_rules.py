"""Тесты бизнес-правил доменного слоя."""

from datetime import date, timedelta, datetime
from decimal import Decimal

import pytest

from app.domain.entities import ContractEntity, RentChargeEntity
from app.domain.rules import (
    compute_charge_status,
    compute_ledger,
    compute_occupancy_rate,
    compute_annual_yield,
    generate_charge_schedule,
    validate_contract_dates,
    validate_status_transition,
)




class TestValidateContractDates:
    """Тесты валидации дат контракта."""

    def test_start_before_end_is_valid(self):
        """start_date < end_date — ошибки нет."""
        future_date = date.today() + timedelta(days=30)
        validate_contract_dates(
            future_date,
            date(future_date.year + 1, 12, 31),
        )

    def test_start_equals_end_raises_error(self):
        """start_date == end_date — ошибка."""
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            validate_contract_dates(date(2026, 1, 1), date(2026, 1, 1))

    def test_start_after_end_raises_error(self):
        """start_date > end_date — ошибка."""
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            validate_contract_dates(date(2026, 12, 31), date(2026, 1, 1))

    def test_start_in_past_is_valid(self):
        """start_date в прошлом — теперь ок."""
        yesterday = date.today() - timedelta(days=1)
        validate_contract_dates(yesterday, date(2027, 1, 1))  # не должно падать

    def test_start_today_is_valid(self):
        """start_date сегодня — ок."""
        validate_contract_dates(date.today(), date(2027, 1, 1))

    def test_start_future_is_valid(self):
        """start_date в будущем — ок."""
        validate_contract_dates(date(2027, 1, 1), date(2027, 12, 31))


class TestComputeChargeStatus:
    """Тесты вычисления статуса начисления."""

    def test_paid_when_total_equals_amount(self):
        """Оплачено полностью."""
        status = compute_charge_status(
            Decimal("1000"), Decimal("1000"), date.today()
        )
        assert status == "paid"

    def test_paid_when_total_exceeds_amount(self):
        """Переплата — paid."""
        status = compute_charge_status(
            Decimal("1000"), Decimal("1500"), date.today()
        )
        assert status == "paid"

    def test_partially_paid(self):
        """Частичная оплата до due_date."""
        tomorrow = date.today() + timedelta(days=1)
        status = compute_charge_status(
            Decimal("1000"), Decimal("500"), tomorrow
        )
        assert status == "partially_paid"

    def test_partially_paid_past_due_is_overdue(self):
        """Частичная оплата после due_date — overdue."""
        yesterday = date.today() - timedelta(days=1)
        status = compute_charge_status(
            Decimal("1000"), Decimal("500"), yesterday
        )
        assert status == "overdue"

    def test_overdue_when_past_due_and_unpaid(self):
        """Просрочено."""
        yesterday = date.today() - timedelta(days=1)
        status = compute_charge_status(
            Decimal("1000"), Decimal("0"), yesterday
        )
        assert status == "overdue"

    def test_pending_when_not_due_and_unpaid(self):
        """Ещё не наступил срок."""
        tomorrow = date.today() + timedelta(days=1)
        status = compute_charge_status(
            Decimal("1000"), Decimal("0"), tomorrow
        )
        assert status == "pending"

    def test_paid_when_overdue_but_fully_paid(self):
        """Просрочен, но оплачен — paid."""
        yesterday = date.today() - timedelta(days=1)
        status = compute_charge_status(
            Decimal("1000"), Decimal("1000"), yesterday
        )
        assert status == "paid"

class TestValidateStatusTransition:
    def test_draft_to_active_valid(self):
        validate_status_transition("draft", "active")

    def test_draft_to_terminated_valid(self):
        validate_status_transition("draft", "terminated")

    def test_active_to_ended_valid(self):
        validate_status_transition("active", "ended")

    def test_ended_to_draft_invalid(self):
        with pytest.raises(ValueError, match="Cannot transition"):
            validate_status_transition("ended", "draft")

    def test_ended_to_anything_invalid(self):
        for status in ["active", "terminated", "overdue", "draft"]:
            with pytest.raises(ValueError):
                validate_status_transition("ended", status)

    def test_active_to_draft_invalid(self):
        with pytest.raises(ValueError, match="Cannot transition"):
            validate_status_transition("active", "draft")

class TestComputeLedger:
    """Тесты финансового состояния контракта."""

    def test_empty_charges(self):
        """Нет начислений — всё по нулям."""
        result = compute_ledger([], Decimal("0"))
        assert result["total_expected"] == Decimal("0")
        assert result["total_paid"] == Decimal("0")
        assert result["outstanding_balance"] == Decimal("0")

    def test_with_charges_and_payments(self):
        """Начисления есть, платежи меньше."""
        charges = [
            RentChargeEntity(
                id="00000000-0000-0000-0000-000000000001",
                account_id="00000000-0000-0000-0000-000000000001",
                contract_id="00000000-0000-0000-0000-000000000001",
                due_date=date(2026, 8, 5),
                period_start=date(2026, 8, 1),
                period_end=date(2026, 9, 1),
                amount=Decimal("1000"),
                currency="RUB",
                status="pending",
            ),
            RentChargeEntity(
                id="00000000-0000-0000-0000-000000000002",
                account_id="00000000-0000-0000-0000-000000000001",
                contract_id="00000000-0000-0000-0000-000000000001",
                due_date=date(2026, 9, 5),
                period_start=date(2026, 9, 1),
                period_end=date(2026, 10, 1),
                amount=Decimal("1000"),
                currency="RUB",
                status="pending",
            ),
        ]
        result = compute_ledger(charges, Decimal("500"))
        assert result["total_expected"] == Decimal("2000")
        assert result["total_paid"] == Decimal("500")
        assert result["outstanding_balance"] == Decimal("1500")


class TestOccupancyRate:
    """Тесты заполняемости."""

    def test_full_occupancy(self):
        assert compute_occupancy_rate(5, 5) == 100.0

    def test_half_occupancy(self):
        assert compute_occupancy_rate(2, 4) == 50.0

    def test_zero_properties(self):
        assert compute_occupancy_rate(0, 0) == 0.0

    def test_more_contracts_than_properties(self):
        """Некорректный кейс, но функция считает честно."""
        assert compute_occupancy_rate(5, 3) == 166.67


class TestAnnualYield:
    """Тесты годовой доходности."""

    def test_positive_yield(self):
        result = compute_annual_yield(
            Decimal("120000"), Decimal("1000000")
        )
        assert result == Decimal("12.00")

    def test_no_purchase_price(self):
        result = compute_annual_yield(Decimal("120000"), None)
        assert result is None

    def test_zero_purchase_price(self):
        result = compute_annual_yield(Decimal("120000"), Decimal("0"))
        assert result is None


class TestGenerateChargeSchedule:
    """Тесты генерации расписания начислений."""

    def test_12_month_schedule(self):
        """Генерация на 12 месяцев."""
        schedule = generate_charge_schedule(
            start_date=date(2026, 8, 1),
            end_date=date(2027, 7, 31),
            rent_amount=Decimal("50000"),
            payment_day=5,
        )
        assert len(schedule) == 12
        # Первый месяц
        assert schedule[0]["due_date"] == date(2026, 8, 5)
        assert schedule[0]["period_start"] == date(2026, 8, 1)
        assert schedule[0]["period_end"] == date(2026, 9, 1)
        assert schedule[0]["amount"] == Decimal("50000")
        # Последний месяц — обрезан по end_date
        assert schedule[-1]["period_end"] == date(2027, 7, 31)

    def test_payment_day_28_clamped(self):
        """День оплаты 31 → clamped to 28."""
        schedule = generate_charge_schedule(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 3, 1),
            rent_amount=Decimal("1000"),
            payment_day=31,
        )
        assert schedule[0]["due_date"] == date(2026, 2, 28)