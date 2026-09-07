"""Pydantic-схемы шаблонов договоров."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ContractTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    name: str
    title: str
    body: str
    property_type: str | None = None
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContractTemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1)
    property_type: str | None = None
    is_default: bool = False


class ContractTemplateUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    title: str | None = Field(None, min_length=1, max_length=300)
    body: str | None = Field(None, min_length=1)
    property_type: str | None = None
    is_default: bool | None = None
