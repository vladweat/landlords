"""DTO для membership."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MembershipDTO(BaseModel):
    """DTO membership."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    user_id: UUID
    role: str
    is_active: bool
    created_at: datetime


class MemberDTO(BaseModel):
    """Участник аккаунта с данными пользователя."""

    user_id: UUID
    email: str
    full_name: str
    phone: str | None = None
    role: str
    is_active: bool
    membership_id: UUID
    created_at: datetime


class MemberUpdateDTO(BaseModel):
    """DTO для смены роли участника."""

    role: str


class AccountUpdateDTO(BaseModel):
    """DTO для обновления настроек аккаунта."""

    name: str | None = None
    base_currency: str | None = None
    timezone: str | None = None
    payment_details: str | None = None
