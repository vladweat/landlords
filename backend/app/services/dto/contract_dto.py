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
    billing_period: str = "monthly"
    payment_day: int = Field(..., ge=1, le=28)
    deposit_amount: Decimal | None = Field(None, ge=0)
    auto_generate_charges: bool = False


class ContractUpdateDTO(BaseModel):
    """DTO для обновления контракта."""

    start_date: date | None = None
    end_date: date | None = None
    rent_amount: Decimal | None = Field(None, gt=0)
    payment_day: int | None = Field(None, ge=1, le=28)
    deposit_amount: Decimal | None = Field(None, ge=0)
    auto_generate_charges: bool | None = None
    status: str | None = Field(None, pattern="^(draft|active|ended|terminated|overdue)$")
    termination_reason: str | None = None