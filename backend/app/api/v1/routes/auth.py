"""Маршруты аутентификации."""

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user_id, get_user_service
from app.api.v1.schemas.user_schema import (
    AuthResponse,
    LoginRequest,
    RegisterRequest,
    UserResponse,
    MeResponse,
)
from app.core.exceptions import ValidationError
from app.services.user_service import UserService
from app.api.responses import success_response, success_list_response

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

@router.post("/register", response_model=AuthResponse)
def register(
    body: RegisterRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Зарегистрировать нового пользователя и создать аккаунт."""
    user_dto, _, token = service.register(body)
    return {
        "status": "success",
        "token": token,
        "user": UserResponse.model_validate(user_dto),
    }


@router.post("/login", response_model=AuthResponse)
def login(
    body: LoginRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Войти в систему."""
    user_dto, _, token = service.login(body.email, body.password)
    return {
        "status": "success",
        "token": token,
        "user": UserResponse.model_validate(user_dto),
    }


@router.get("/me", response_model=MeResponse)
def get_me(
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Получить текущего пользователя."""
    user_dto, _ = service.get_me(user_id)
    return {
        "status": "success",
        "user": UserResponse.model_validate(user_dto),
    }
    
from app.api.v1.schemas.user_schema import (
    ForgotPasswordRequest, ResetPasswordRequest,
    UpdateProfileRequest, ChangePasswordRequest, DeleteAccountRequest,
)
from app.core.security import create_reset_token, verify_reset_token
from app.core.security import create_reset_token, verify_reset_token
from loguru import logger

@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Запросить сброс пароля."""
    user = service.get_user_by_email(body.email)
    if user:
        token = create_reset_token(str(user.id))
        logger.info(f"Reset token for {body.email}: {token}")
    return {"message": "Если аккаунт с таким email существует, инструкция отправлена на почту."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Сбросить пароль по токену."""
    user_id = verify_reset_token(body.token)
    if not user_id:
        raise ValidationError("Токен устарел или недействителен. Запросите восстановление заново.")
    service.reset_password(UUID(user_id), body.new_password)
    return {"message": "Пароль успешно изменён."}


@router.put("/me")
def update_profile(
    body: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Обновить профиль."""
    dto = service.update_profile(user_id, body.full_name)
    return {"status": "success", "data": UserResponse.model_validate(dto).model_dump()}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Сменить пароль."""
    service.change_password(user_id, body.current_password, body.new_password)
    return {"message": "Пароль успешно изменён."}


@router.delete("/me")
def delete_account(
    body: DeleteAccountRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Удалить аккаунт."""
    service.delete_account(user_id, body.confirmation)
    return {"message": "Аккаунт удалён."}