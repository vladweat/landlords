"""Pydantic-схемы для начислений."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RentChargeResponse(BaseModel):
    """Ответ с данными начисления."""

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
    reminder_status: dict | None = None



class RentChargeListResponse(BaseModel):
    """Ответ со списком начислений."""

    status: str = "success"
    data: list[RentChargeResponse]


class RentChargeSingleResponse(BaseModel):
    """Ответ с одним начислением."""

    status: str = "success"
    data: RentChargeResponse