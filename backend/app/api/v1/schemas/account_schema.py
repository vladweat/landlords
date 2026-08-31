"""Pydantic-схемы для аккаунтов."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountResponse(BaseModel):
    """Ответ с данными аккаунта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    base_currency: str
    timezone: str