"""Схемы для событий контракта."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


from pydantic import field_validator

class ContractEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    contract_id: UUID
    event_type: str
    title: str
    description: str | None = None
    event_metadata: dict | None = None
    created_by: UUID | None = None
    created_at: datetime


class CreateNoteRequest(BaseModel):
    """Запрос на создание заметки."""

    title: str = Field(..., max_length=255)
    description: str | None = None