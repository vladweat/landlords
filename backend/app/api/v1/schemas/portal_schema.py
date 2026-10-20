"""Pydantic-схемы публичного портала арендатора."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PortalLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    portal_token: str
    share_url: str
    portal_token_expires_at: datetime


class PortalLinkSingleResponse(BaseModel):
    status: str = "success"
    data: PortalLinkResponse


class PortalHistoryLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    type: str
    description: str
    amount: Decimal
    balance: Decimal


class PortalOpenChargeResponse(BaseModel):
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


class PaymentClaimResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID
    charge_id: UUID | None = None
    amount: Decimal | None = None
    note: str | None = None
    status: str
    created_at: datetime
    resolved_at: datetime | None = None


class PaymentClaimSingleResponse(BaseModel):
    status: str = "success"
    data: PaymentClaimResponse


class PaymentClaimListResponse(BaseModel):
    status: str = "success"
    data: list[PaymentClaimResponse]


class PublicPortalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    landlord_name: str
    property_address: str
    tenant_name: str
    currency: str
    outstanding_balance: Decimal
    total_expected: Decimal
    total_paid: Decimal
    payment_details: str | None = None
    history: list[PortalHistoryLineResponse]
    open_charges: list[PortalOpenChargeResponse]
    pending_claim: PaymentClaimResponse | None = None


class PublicPortalSingleResponse(BaseModel):
    status: str = "success"
    data: PublicPortalResponse


class CreatePaymentClaimRequest(BaseModel):
    charge_id: UUID | None = None
    amount: Decimal | None = None
    note: str | None = Field(default=None, max_length=500)
