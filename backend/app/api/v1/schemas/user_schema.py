"""Pydantic-схемы для пользователей."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserResponse(BaseModel):
    """Ответ с данными пользователя."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    phone: str | None = None
    is_active: bool


class RegisterRequest(BaseModel):
    """Запрос на регистрацию."""

    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    """Запрос на вход."""

    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Ответ с токеном."""

    status: str = "success"
    token: str
    user: UserResponse
    
class MeResponse(BaseModel):
    """Ответ для /auth/me."""
    status: str = "success"
    user: UserResponse
    
class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UpdateProfileRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountRequest(BaseModel):
    confirmation: str