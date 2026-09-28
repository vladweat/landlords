"""DTO для дашборда и ledger."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LedgerLineDTO(BaseModel):
    """DTO строки ledger."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    type: str
    description: str
    amount: Decimal
    balance: Decimal
    reminder_status: dict | None = None
    source_id: UUID | None = None
    created_at: datetime | None = None


class LedgerDTO(BaseModel):
    """DTO финансового состояния контракта (построчный)."""

    model_config = ConfigDict(from_attributes=True)

    total_expected: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    lines: list[LedgerLineDTO]
    last_payment_date: date | None = None
    overdue_days: int = 0


class DashboardSummaryDTO(BaseModel):
    monthly_expected_income: Decimal
    monthly_collected_income: Decimal
    outstanding_balance: Decimal
    occupancy_rate: float
    active_properties: int
    active_contracts: int
    monthly_income_previous: Decimal = Decimal("0")
    monthly_income_change_percent: float = 0.0
    overdue_total_amount: Decimal = Decimal("0")
    overdue_count: int = 0
    properties_overview: list[dict] = []