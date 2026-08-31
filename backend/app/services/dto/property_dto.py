"""DTO для объектов недвижимости."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from uuid import UUID
from datetime import date


class ActiveContractDTO(BaseModel):
    """DTO активного контракта для встраивания в PropertyDTO."""

    id: UUID
    tenant_name: str
    status: str
    end_date: date

class PropertyDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    city: str
    street: str
    house: str
    building: str | None = None
    apartment: str | None = None
    type: str
    size_m2: float
    purchase_price: Decimal | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    active_contract: ActiveContractDTO | None = None

    def get_address(self) -> str:
        parts = [f"г. {self.city}", f"ул. {self.street}", f"д. {self.house}"]
        if self.building:
            parts.append(f"корп. {self.building}")
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)



class PropertyCreateDTO(BaseModel):
    city: str = Field(..., max_length=255)
    street: str = Field(..., max_length=500)
    house: str = Field(..., max_length=50)
    building: str | None = Field(None, max_length=50)
    apartment: str | None = Field(None, max_length=50)
    type: str = Field(..., pattern="^(apartment|house|room)$")
    size_m2: float = Field(..., gt=0)
    purchase_price: Decimal | None = Field(None, ge=0)


class PropertyUpdateDTO(BaseModel):
    city: str | None = Field(None, max_length=255)
    street: str | None = Field(None, max_length=500)
    house: str | None = Field(None, max_length=50)
    building: str | None = Field(None, max_length=50)
    apartment: str | None = Field(None, max_length=50)
    type: str | None = Field(None, pattern="^(apartment|house|room)$")
    size_m2: float | None = Field(None, gt=0)
    purchase_price: Decimal | None = Field(None, ge=0)
    status: str | None = Field(None, pattern="^(active|inactive|archived)$")
    
