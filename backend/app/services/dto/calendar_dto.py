"""DTO событий календаря платежей."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CalendarEventDTO(BaseModel):
    """Событие календаря: начисление к оплате или окончание договора."""

    model_config = ConfigDict(from_attributes=True)

    type: Literal["charge_due", "contract_ending"]
    date: date
    contract_id: UUID
    property_address: str = ""
    tenant_name: str = ""
    charge_id: UUID | None = None
    amount: Decimal | None = None
    amount_paid: Decimal | None = None
    remaining: Decimal | None = None
    status: str | None = None
    currency: str | None = None
    rent_amount: Decimal | None = None
    days_until_end: int | None = None
