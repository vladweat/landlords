"""Pydantic-схемы для аккаунтов и участников."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccountResponse(BaseModel):
    """Ответ с данными аккаунта."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_id: UUID
    base_currency: str
    timezone: str


class AccountUpdateRequest(BaseModel):
    """Запрос на обновление настроек аккаунта."""

    name: str | None = None
    base_currency: str | None = None
    timezone: str | None = None


class AccountSingleResponse(BaseModel):
    """Обёртка ответа с аккаунтом."""

    status: str = "success"
    data: AccountResponse


class MemberResponse(BaseModel):
    """Участник аккаунта."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool
    membership_id: UUID
    created_at: datetime


class MemberCreateRequest(BaseModel):
    """Создание участника."""

    email: EmailStr
    full_name: str
    password: str = Field(min_length=6)
    role: str


class MemberUpdateRequest(BaseModel):
    """Смена роли участника."""

    role: str


class MemberListResponse(BaseModel):
    status: str = "success"
    data: list[MemberResponse]


class MemberSingleResponse(BaseModel):
    status: str = "success"
    data: MemberResponse
