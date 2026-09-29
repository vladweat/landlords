"""DTO публичного портала арендатора и заявок «я оплатил»."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PortalLinkDTO(BaseModel):
    """Ссылка на портал договора для CRM."""

    model_config = ConfigDict(from_attributes=True)

    portal_token: str
    share_url: str


class PortalHistoryLineDTO(BaseModel):
    """Упрощённая строка истории для арендатора."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    type: str
    description: str
    amount: Decimal
    balance: Decimal


class PortalOpenChargeDTO(BaseModel):
    """Открытое начисление со ссылкой на квитанцию."""

    model_config = ConfigDict(from_attributes=True)

    charge_id: UUID
    period_start: date
    period_end: date
    due_date: date
    amount: Decimal
    amount_paid: Decimal
    amount_remaining: Decimal
    currency: str
    status: str
    invoice_url: str | None = None


class PortalClaimDTO(BaseModel):
    """Заявка «я оплатил»."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    charge_id: UUID | None = None
    amount: Decimal | None = None
    note: str | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None


class PublicPortalDTO(BaseModel):
    """Публичные данные портала арендатора."""

    model_config = ConfigDict(from_attributes=True)

    landlord_name: str
    property_address: str
    tenant_name: str
    currency: str
    outstanding_balance: Decimal
    total_expected: Decimal
    total_paid: Decimal
    payment_details: str | None = None
    history: list[PortalHistoryLineDTO]
    open_charges: list[PortalOpenChargeDTO]
    pending_claim: PortalClaimDTO | None = None


class CreatePaymentClaimDTO(BaseModel):
    """Тело создания claim от арендатора."""

    charge_id: UUID | None = None
    amount: Decimal | None = None  # обязательна в create_claim; на квитанции может подставиться
    note: str | None = Field(default=None, max_length=500)
