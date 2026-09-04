"""DTO для начислений."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RentChargeDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    contract_id: UUID
    due_date: date
    period_start: date
    period_end: date
    amount: Decimal
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    amount_paid: Decimal = Decimal("0")
    reminder_status: dict | None = None
    


class RentChargeCreateDTO(BaseModel):
    """DTO для создания начисления."""

    contract_id: UUID
    due_date: date
    period_start: date
    period_end: date
    amount: Decimal
    currency: str = "RUB"