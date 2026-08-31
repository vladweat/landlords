"""DTO для арендаторов."""

from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TenantContractDTO(BaseModel):
    """DTO контракта для встраивания в TenantDTO."""

    id: UUID
    property_address: str
    status: str
    rent_amount: Decimal
    end_date: date


class TenantDTO(BaseModel):
    """DTO арендатора."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    active_contracts: list[TenantContractDTO] = []


class TenantCreateDTO(BaseModel):
    """DTO для создания арендатора."""

    full_name: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None


class TenantUpdateDTO(BaseModel):
    """DTO для обновления арендатора."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None