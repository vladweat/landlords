"""Бизнес-правила и доменные сервисы (чистые функции)."""

from datetime import date, datetime, timezone
from typing import Sequence
from uuid import UUID

from app.domain.entities import ContractEntity, LedgerLine, PaymentEntity, RentChargeEntity

def compute_contract_status(contract: ContractEntity) -> str:
    """Вычислить статус контракта на основе дат."""
    today = datetime.now(timezone.utc).date()

    if contract.status in ("ended", "terminated"):
        return contract.status

    if contract.start_date > today:
        return "draft"

    if contract.end_date < today:
        return "ended"

    # Если есть задолженность — overdue (будет вычисляться при интеграции с RentCharge)
    # Пока просто active
    return "active"


def is_contract_active(contract: ContractEntity) -> bool:
    """Проверить, активен ли контракт."""
    return compute_contract_status(contract) == "active"


def validate_contract_dates(start_date: date, end_date: date) -> None:
    """Проверить корректность дат контракта.

    Разрешает даты в прошлом — пользователь может вносить
    существующие договоры задним числом.

    Raises:
        ValueError: Если даты некорректны.
    """
    if start_date >= end_date:
        raise ValueError("start_date must be before end_date")
    
from decimal import Decimal


def compute_charge_status(charge_amount: Decimal, total_paid: Decimal, due_date: date) -> str:
    """Вычислить статус начисления на основе суммы платежей и даты.

    Args:
        charge_amount: сумма начисления.
        total_paid: общая сумма платежей по начислению.
        due_date: дата оплаты.

    Returns:
        Статус: paid, partially_paid, overdue, pending.
    """
    today = datetime.now(timezone.utc).date()

    if total_paid >= charge_amount:
        return "paid"
    if due_date < today:
        return "overdue"
    if total_paid > 0:
        return "partially_paid"
    return "pending"
    
    
def compute_ledger(
    charges: Sequence[RentChargeEntity],
    total_paid: Decimal,
) -> dict:
    """Вычислить финансовое состояние контракта.

    Args:
        charges: список начислений по контракту.
        total_paid: общая сумма платежей.

    Returns:
        Словарь с total_expected, total_paid, outstanding_balance.
    """
    total_expected = sum((c.amount for c in charges), Decimal("0"))
    outstanding = total_expected - total_paid
    return {
        "total_expected": total_expected,
        "total_paid": total_paid,
        "outstanding_balance": outstanding,
    }


def compute_occupancy_rate(
    active_contracts: int,
    active_properties: int,
) -> float:
    """Вычислить заполняемость.

    Args:
        active_contracts: количество активных контрактов.
        active_properties: количество активных объектов.

    Returns:
        Процент заполняемости (0-100).
    """
    if active_properties == 0:
        return 0.0
    return round((active_contracts / active_properties) * 100, 2)


def compute_annual_yield(
    annual_rent: Decimal,
    purchase_price: Decimal,
) -> Decimal | None:
    """Вычислить годовую доходность.

    Args:
        annual_rent: годовая арендная плата.
        purchase_price: цена покупки.

    Returns:
        Доходность в процентах или None.
    """
    if not purchase_price or purchase_price == 0:
        return None
    return round((annual_rent / purchase_price) * 100, 2)

from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta


def generate_charge_schedule(
    start_date: date,
    end_date: date,
    rent_amount: Decimal,
    payment_day: int,
    billing_period: str = "monthly",
) -> list[dict]:
    """Сгенерировать расписание начислений по периоду оплаты.

    Args:
        start_date: дата начала контракта.
        end_date: дата окончания контракта.
        rent_amount: сумма за один период оплаты.
        payment_day: день оплаты (1-28).
        billing_period: monthly | quarterly | yearly.

    Returns:
        Список словарей с due_date, period_start, period_end, amount.
        Короткий первый/последний период — prorate; due_date не раньше period_start.
    """
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}.get(billing_period, 1)
    charges = []
    current = start_date

    while current < end_date:
        period_start = current
        full_period_end = period_start + relativedelta(months=months)
        period_end = full_period_end if full_period_end <= end_date else end_date

        if period_end < full_period_end:
            amount = prorate_charge_amount(
                rent_amount, period_start, full_period_end, period_end
            )
        else:
            amount = rent_amount

        if amount <= 0:
            current = period_end
            continue

        raw_due = date(period_start.year, period_start.month, min(payment_day, 28))
        due_date = max(raw_due, period_start)

        charges.append({
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "amount": amount,
        })

        current = period_end

    return charges


VALID_CONTRACT_TRANSITIONS = {
    "draft": {"active", "terminated"},
    "active": {"ended", "terminated", "overdue"},
    "ended": set(),           # конечное состояние
    "terminated": set(),      # конечное состояние
    "overdue": {"active", "ended", "terminated"},
}


def validate_status_transition(current_status: str, new_status: str) -> None:
    """Проверить, разрешён ли переход между статусами контракта.

    Raises:
        ValueError: Если переход не разрешён.
    """
    allowed = VALID_CONTRACT_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{current_status}' to '{new_status}'"
        )
        
def compute_ledger_lines(
    charges: list[RentChargeEntity],
    payments: list[PaymentEntity],
) -> list[LedgerLine]:
    """Построить построчный ledger с running balance.

    Объединяет начисления и платежи в один список,
    сортирует по (date, type_order, created_at, source_id), считает накопительный баланс.
    """
    lines: list[LedgerLine] = []
    balance = Decimal("0")

    for charge in charges:
        lines.append(LedgerLine(
            date=charge.due_date,
            type="charge",
            description=f"Начисление за период {charge.period_start} — {charge.period_end}",
            amount=charge.amount,
            balance=Decimal("0"),
            source_id=charge.id,
            created_at=charge.created_at,
        ))

    for payment in payments:
        lines.append(LedgerLine(
            date=payment.date_paid,
            type="payment",
            description=f"Платёж ({payment.method})",
            amount=-payment.amount,
            balance=Decimal("0"),
            source_id=payment.id,
            created_at=payment.created_at,
        ))

    def _sort_key(line: LedgerLine) -> tuple:
        type_order = 0 if line.type == "charge" else 1
        created = line.created_at or datetime.min.replace(tzinfo=timezone.utc)
        source = str(line.source_id) if line.source_id else ""
        return (line.date, type_order, created, source)

    lines.sort(key=_sort_key)

    for line in lines:
        balance += line.amount
        line.balance = balance

    return lines

def validate_payment_day(day: int) -> None:
    """Проверить, что день платежа корректен (1-28).

    28 — максимально безопасное значение для всех месяцев.
    """
    if not (1 <= day <= 28):
        raise ValueError("payment_day must be between 1 and 28")


def prorate_charge_amount(
    amount: Decimal,
    period_start: date,
    period_end: date,
    cut_date: date,
) -> Decimal:
    """Пропорционально уменьшить сумму начисления до cut_date.

    Считает по календарным дням периода [period_start, period_end).
    """
    total_days = (period_end - period_start).days
    if total_days <= 0:
        return Decimal("0.00")
    if cut_date <= period_start:
        return Decimal("0.00")
    if cut_date >= period_end:
        return amount
    used_days = (cut_date - period_start).days
    return (amount * Decimal(used_days) / Decimal(total_days)).quantize(Decimal("0.01"))


def plan_charges_on_terminate(
    charges: Sequence[RentChargeEntity],
    paid_by_charge: dict[UUID, Decimal],
    effective_date: date,
) -> tuple[list[UUID], list[tuple[UUID, Decimal, date]]]:
    """Спланировать пересчёт начислений при расторжении.

    Returns:
        (ids_to_delete, updates) где updates = [(id, new_amount, new_period_end), ...]
    """
    to_delete: list[UUID] = []
    to_update: list[tuple[UUID, Decimal, date]] = []

    for charge in charges:
        paid = paid_by_charge.get(charge.id, Decimal("0"))

        # Будущие периоды — удаляем (платежи отвязываются в сервисе → аванс)
        if charge.period_start >= effective_date:
            to_delete.append(charge.id)
            continue

        # Текущий период, пересекающий дату расторжения
        if charge.period_start < effective_date < charge.period_end:
            if paid >= charge.amount:
                # Уже полностью оплачен — только укорачиваем период
                to_update.append((charge.id, charge.amount, effective_date))
                continue
            new_amount = prorate_charge_amount(
                charge.amount, charge.period_start, charge.period_end, effective_date
            )
            if new_amount < paid:
                new_amount = paid
            if new_amount == 0 and paid == 0:
                to_delete.append(charge.id)
            else:
                to_update.append((charge.id, new_amount, effective_date))

    return to_delete, to_update


def plan_charges_on_renew(
    existing: Sequence[RentChargeEntity],
    old_end_date: date,
    new_end_date: date,
    rent_amount: Decimal,
    payment_day: int,
    billing_period: str = "monthly",
) -> list[dict]:
    """Спланировать новые начисления при продлении договора.

    Генерирует расписание от старой даты окончания до новой,
    пропуская периоды, которые уже есть (по period_start).
    """
    if new_end_date <= old_end_date:
        raise ValueError("new_end_date must be after current end_date")

    existing_starts = {c.period_start for c in existing}
    schedule = generate_charge_schedule(
        start_date=old_end_date,
        end_date=new_end_date,
        rent_amount=rent_amount,
        payment_day=payment_day,
        billing_period=billing_period,
    )
    return [item for item in schedule if item["period_start"] not in existing_starts]