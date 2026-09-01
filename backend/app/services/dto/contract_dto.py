"""DTO для контрактов."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractDTO(BaseModel):
    """DTO контракта."""

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


class ContractCreateDTO(BaseModel):
    """DTO для создания контракта."""

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


class ContractUpdateDTO(BaseModel):
    """DTO для обновления контракта."""

    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = Field(None, gt=0)
    billing_period: str | None = Field(None, pattern="^(monthly|quarterly|yearly)$")
    payment_day: int | None = Field(None, ge=1, le=28)
    deposit_amount: Decimal | None = Field(None, ge=0)
    auto_generate_charges: bool | None = None
    status: str | None = Field(None, pattern="^(draft|active|ended|terminated|overdue)$")
    termination_reason: str | None = None


class ContractTerminateDTO(BaseModel):
    """DTO расторжения договора."""

    effective_date: date
    termination_reason: str = Field(..., min_length=1, max_length=500)
    generate_act: bool = True


class ContractRenewDTO(BaseModel):
    """DTO продления договора."""

    new_end_date: date
    new_rent_amount: Decimal | None = Field(None, gt=0)
    generate_act: bool = True


class ContractLifecycleResultDTO(BaseModel):
    """Результат продления / расторжения."""

    contract: ContractDTO
    charges_deleted: int = 0
    charges_updated: int = 0
    charges_created: int = 0
    document_id: UUID | None = None
    document_url: str | None = None
    document_filename: str | None = None