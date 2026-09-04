"""Pydantic-схемы календаря платежей."""

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CalendarEventResponse(BaseModel):
    """Событие календаря в ответе API."""

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


class CalendarEventsData(BaseModel):
    items: list[CalendarEventResponse] = Field(default_factory=list)


class CalendarEventsResponse(BaseModel):
    status: str = "success"
    data: CalendarEventsData
