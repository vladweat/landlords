"""Pydantic-схемы для платежей."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentResponse(BaseModel):
    """Ответ с данными платежа."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    contract_id: UUID
    rent_charge_id: UUID | None = None
    date_paid: date
    amount: Decimal
    currency: str
    method: str
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class PaymentCreateRequest(BaseModel):
    """Запрос на создание платежа."""

    contract_id: UUID
    rent_charge_id: UUID | None = None
    date_paid: date
    amount: Decimal = Field(..., gt=0)
    method: str = "transfer"
    note: str | None = None


class PaymentUpdateRequest(BaseModel):
    """Запрос на обновление платежа."""

    date_paid: date | None = None
    amount: Decimal | None = Field(None, gt=0)
    method: str | None = None
    note: str | None = None


class PaymentListResponse(BaseModel):
    """Ответ со списком платежей."""

    status: str = "success"
    data: list[PaymentResponse]


class PaymentSingleResponse(BaseModel):
    """Ответ с одним платежом."""

    status: str = "success"
    data: PaymentResponse