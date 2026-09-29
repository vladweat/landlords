"""DTO для аккаунта."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountDTO(BaseModel):
    """DTO аккаунта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    base_currency: str
    timezone: str
    payment_details: str | None = None
    plan: str = "free"
    subscription_status: str = "none"
    subscription_period_end: datetime | None = None
    created_at: datetime


class AccountCreateDTO(BaseModel):
    """DTO для создания аккаунта."""

    name: str
    base_currency: str = "RUB"
    timezone: str = "Europe/Moscow"
    payment_details: str | None = None
