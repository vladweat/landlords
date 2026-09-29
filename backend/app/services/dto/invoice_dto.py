"""DTO квитанций."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InvoiceDTO(BaseModel):
    """Квитанция в CRM."""

    model_config = ConfigDict(from_attributes=True)

    invoice_id: UUID
    charge_id: UUID
    contract_id: UUID
    document_id: UUID | None = None
    share_url: str
    public_token: str


class PublicInvoiceDTO(BaseModel):
    """Публичные данные квитанции (минимум PII)."""

    landlord_name: str
    property_address: str
    tenant_name: str
    period_start: date
    period_end: date
    due_date: date
    amount: Decimal
    amount_paid: Decimal
    amount_remaining: Decimal
    currency: str
    status: str
    payment_details: str | None = None
    filename: str | None = None
    has_pending_claim: bool = False
