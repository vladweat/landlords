"""Бизнес-правила и доменные сервисы (чистые функции)."""

from datetime import date, datetime, timezone

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
    elif total_paid > 0:
        return "partially_paid"
    elif due_date < today:
        return "overdue"
    else:
        return "pending"
    
    
from decimal import Decimal
from datetime import date
from typing import Sequence

from app.domain.entities import ContractEntity, RentChargeEntity


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
) -> list[dict]:
    """Сгенерировать расписание начислений по месяцам.

    Args:
        start_date: дата начала контракта.
        end_date: дата окончания контракта.
        rent_amount: ежемесячная сумма.
        payment_day: день оплаты (1-28).

    Returns:
        Список словарей с due_date, period_start, period_end, amount.
    """
    charges = []
    current = start_date

    while current < end_date:
        # Период: с current по current + 1 месяц
        period_start = current
        period_end = period_start + relativedelta(months=1)

        # Не выходим за end_date
        if period_end > end_date:
            period_end = end_date

        # Дата оплаты — payment_day месяца period_start
        due_date = date(period_start.year, period_start.month, min(payment_day, 28))

        charges.append({
            "due_date": due_date,
            "period_start": period_start,
            "period_end": period_end,
            "amount": rent_amount,
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
    сортирует по дате, считает накопительный баланс.
    """
    lines: list[LedgerLine] = []
    balance = Decimal("0")

    # Добавляем charges
    for charge in charges:
        lines.append(LedgerLine(
            date=charge.due_date,
            type="charge",
            description=f"Начисление за период {charge.period_start} — {charge.period_end}",
            amount=charge.amount,
            balance=Decimal("0"),  # будет пересчитано
        ))

    # Добавляем payments
    for payment in payments:
        lines.append(LedgerLine(
            date=payment.date_paid,
            type="payment",
            description=f"Платёж ({payment.method})",
            amount=-payment.amount,  # отрицательное
            balance=Decimal("0"),
        ))

    # Сортируем по дате
    lines.sort(key=lambda x: x.date)

    # Считаем running balance
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