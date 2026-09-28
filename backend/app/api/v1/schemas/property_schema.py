"""Pydantic-схемы для объектов недвижимости."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.api.v1.schemas.common import PaginatedData

class ActiveContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    tenant_name: str
    status: str
    end_date: date


class PropertyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    city: str
    street: str
    house: str
    building: str | None = None
    apartment: str | None = None
    address: str = ""
    type: str
    size_m2: float
    purchase_price: Decimal | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    active_contract: ActiveContractResponse | None = None
    roi: dict | None = None

class PropertyCreateRequest(BaseModel):
    city: str = Field(..., max_length=255)
    street: str = Field(..., max_length=500)
    house: str = Field(..., max_length=50)
    building: str | None = Field(None, max_length=50)
    apartment: str | None = Field(None, max_length=50)
    type: str = Field(..., pattern="^(apartment|house|room|commercial)$")
    size_m2: float = Field(..., gt=0)
    purchase_price: Decimal | None = Field(None, ge=0)


class PropertyUpdateRequest(BaseModel):
    city: str | None = Field(None, max_length=255)
    street: str | None = Field(None, max_length=500)
    house: str | None = Field(None, max_length=50)
    building: str | None = Field(None, max_length=50)
    apartment: str | None = Field(None, max_length=50)
    type: str | None = Field(None, pattern="^(apartment|house|room|commercial)$")
    size_m2: float | None = Field(None, gt=0)
    purchase_price: Decimal | None = Field(None, ge=0)
    status: str | None = Field(None, pattern="^(active|inactive|archived)$")



class PropertyListResponse(BaseModel):
    status: str = "success"
    data: PaginatedData


class PropertySingleResponse(BaseModel):
    """Ответ с одним объектом."""

    status: str = "success"
    data: PropertyResponse