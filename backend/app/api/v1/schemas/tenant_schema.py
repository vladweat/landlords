"""Pydantic-схемы для арендаторов."""

from datetime import datetime, date
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from app.api.v1.schemas.common import PaginatedData

class TenantContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    property_address: str
    status: str
    rent_amount: Decimal
    end_date: date


class TenantResponse(BaseModel):
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
    active_contracts: list[TenantContractResponse] = []


class TenantCreateRequest(BaseModel):
    full_name: str = Field(..., max_length=255)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    notes: str | None = Field(None, max_length=1000)


class TenantUpdateRequest(BaseModel):
    """Запрос на обновление арендатора."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool | None = None





class TenantListResponse(BaseModel):
    status: str = "success"
    data: PaginatedData


class TenantSingleResponse(BaseModel):
    """Ответ с одним арендатором."""

    status: str = "success"
    data: TenantResponse