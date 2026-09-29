"""DTO для приглашений в аккаунт."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InviteCreateDTO(BaseModel):
    """Создание приглашения."""

    email: EmailStr
    full_name: str
    role: str


class InviteDTO(BaseModel):
    """Приглашение для owner."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    email: str
    full_name: str
    role: str
    token: str
    invite_url: str
    expires_at: datetime
    invited_by_user_id: UUID
    created_at: datetime


class InvitePreviewDTO(BaseModel):
    """Публичный preview приглашения."""

    email: str
    full_name: str
    role: str
    account_name: str
    expires_at: datetime


class InviteAcceptDTO(BaseModel):
    """Принятие приглашения."""

    password: str = Field(min_length=6)
    full_name: str | None = None
