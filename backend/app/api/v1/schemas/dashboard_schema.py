"""Pydantic-схемы для дашборда."""

from decimal import Decimal

from pydantic import BaseModel


from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    monthly_expected_income: Decimal
    monthly_collected_income: Decimal
    outstanding_balance: Decimal
    occupancy_rate: float
    active_properties: int
    active_contracts: int
    monthly_income_previous: Decimal = Decimal("0")
    monthly_income_change_percent: float = 0.0
    overdue_total_amount: Decimal = Decimal("0")
    portfolio_roi: dict | None = None
    properties_overview: list[dict] = []


class DashboardResponse(BaseModel):
    """Полный ответ дашборда."""

    status: str = "success"
    data: DashboardSummaryResponse