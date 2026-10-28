"""Pydantic-схемы для пользователей."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr

from app.api.v1.schemas.account_schema import AccountResponse


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


class AuthData(BaseModel):
    """Данные успешной аутентификации."""

    token: str | None = None
    user: UserResponse


class AuthResponse(BaseModel):
    """Стандартный успешный ответ аутентификации."""

    status: str = "success"
    data: AuthData


class MessageData(BaseModel):
    """Сообщение успешной операции."""

    message: str


class MessageResponse(BaseModel):
    """Стандартный ответ операции с сообщением."""

    status: str = "success"
    data: MessageData


class UserSingleResponse(BaseModel):
    """Стандартный ответ с пользователем."""

    status: str = "success"
    data: UserResponse


class MeData(BaseModel):
    """Данные текущего пользователя, аккаунта и роли."""

    user: UserResponse
    account: AccountResponse
    role: str


class MeResponse(BaseModel):
    """Ответ для /auth/me."""

    status: str = "success"
    data: MeData


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
