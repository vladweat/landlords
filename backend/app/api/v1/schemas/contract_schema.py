"""Pydantic-схемы для контрактов."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.api.v1.schemas.common import PaginatedData

class ContractResponse(BaseModel):
    """Ответ с данными контракта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    property_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    rent_amount: Decimal
    currency: str
    billing_period: str
    payment_day: int
    deposit_amount: Decimal | None = None
    auto_generate_charges: bool
    status: str
    termination_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ContractCreateRequest(BaseModel):
    """Запрос на создание контракта."""

    property_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    rent_amount: Decimal = Field(..., gt=0)
    currency: str = "RUB"
    billing_period: str = Field(default="monthly", pattern="^(monthly|quarterly|yearly)$")
    payment_day: int = Field(..., ge=1, le=28)
    deposit_amount: Decimal | None = Field(None, ge=0)
    auto_generate_charges: bool = False


class ContractUpdateRequest(BaseModel):
    """Запрос на обновление контракта."""

    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = Field(None, gt=0)
    billing_period: str | None = Field(None, pattern="^(monthly|quarterly|yearly)$")
    payment_day: int | None = Field(None, ge=1, le=28)
    deposit_amount: Decimal | None = Field(None, ge=0)
    auto_generate_charges: bool | None = None
    status: str | None = Field(None, pattern="^(draft|active|ended|terminated|overdue)$")
    termination_reason: str | None = Field(None, max_length=500)


class ContractTerminateRequest(BaseModel):
    """Запрос на расторжение договора."""

    effective_date: date
    termination_reason: str = Field(..., min_length=1, max_length=500)
    generate_act: bool = True


class ContractRenewRequest(BaseModel):
    """Запрос на продление договора."""

    new_end_date: date
    new_rent_amount: Decimal | None = Field(None, gt=0)
    generate_act: bool = True


class ContractLifecycleResponse(BaseModel):
    """Ответ продления / расторжения."""

    model_config = ConfigDict(from_attributes=True)

    contract: ContractResponse
    charges_deleted: int = 0
    charges_updated: int = 0
    charges_created: int = 0
    document_id: UUID | None = None
    document_url: str | None = None
    document_filename: str | None = None


class ContractLifecycleSingleResponse(BaseModel):
    status: str = "success"
    data: ContractLifecycleResponse


class ContractListResponse(BaseModel):
    status: str = "success"
    data: PaginatedData


class ContractSingleResponse(BaseModel):
    """Ответ с одним контрактом."""

    status: str = "success"
    data: ContractResponse
    
class LedgerLineResponse(BaseModel):
    """Схема строки ledger."""

    model_config = ConfigDict(from_attributes=True)

    date: date
    type: str
    description: str
    amount: Decimal
    balance: Decimal
    reminder_status: dict | None = None
    source_id: UUID | None = None
    created_at: datetime | None = None


class LedgerResponse(BaseModel):
    """Ответ с финансовым состоянием контракта."""

    model_config = ConfigDict(from_attributes=True)

    total_expected: Decimal
    total_paid: Decimal
    outstanding_balance: Decimal
    lines: list[LedgerLineResponse]
    last_payment_date: date | None = None
    overdue_days: int = 0

class ContractLedgerResponse(BaseModel):
    """Полный ответ ledger."""

    status: str = "success"
    data: LedgerResponse