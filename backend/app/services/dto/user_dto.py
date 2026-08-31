"""DTO для пользователя."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserDTO(BaseModel):
    """DTO пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_active: bool
    created_at: datetime


class UserCreateDTO(BaseModel):
    """DTO для создания пользователя."""

    email: str
    password: str
    full_name: str