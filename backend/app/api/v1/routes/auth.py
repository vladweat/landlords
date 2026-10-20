"""Маршруты аутентификации."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, Response

from app.api.deps import (
    get_auth_session_service,
    get_current_user_id,
    get_user_service,
)
from app.api.v1.schemas.account_schema import AccountResponse
from app.api.v1.schemas.user_schema import (
    AuthResponse,
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MeData,
    MeResponse,
    RegisterRequest,
    ResetPasswordRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.core.config import settings
from app.core.cookies import ACCESS_TOKEN_COOKIE, clear_access_cookie, set_access_cookie
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.security import verify_reset_token
from app.services.auth_session_service import AuthSessionService
from app.services.user_service import UserService

router = APIRouter(prefix="/v1/auth", tags=["Auth"])


@router.post("/register", response_model=AuthResponse, response_model_exclude_none=True)
def register(
    body: RegisterRequest,
    response: Response,
    return_bearer_token: bool = Header(False, alias="X-Return-Bearer-Token"),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Зарегистрировать нового пользователя и создать аккаунт."""
    if not settings.ALLOW_PUBLIC_REGISTRATION:
        raise ForbiddenError("Регистрация закрыта")
    user_dto, _, token = service.register(body)
    set_access_cookie(response, token)
    return {
        "status": "success",
        "token": token if return_bearer_token else None,
        "user": UserResponse.model_validate(user_dto),
    }


@router.post("/login", response_model=AuthResponse, response_model_exclude_none=True)
def login(
    body: LoginRequest,
    response: Response,
    return_bearer_token: bool = Header(False, alias="X-Return-Bearer-Token"),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Войти в систему."""
    user_dto, _, token = service.login(body.email, body.password)
    set_access_cookie(response, token)
    return {
        "status": "success",
        "token": token if return_bearer_token else None,
        "user": UserResponse.model_validate(user_dto),
    }


@router.get("/me", response_model=MeResponse)
def get_me(
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    """Получить текущего пользователя, аккаунт и роль.

    Если сессия ещё в Bearer (старый localStorage), перекладываем JWT в cookie.
    """
    if authorization and authorization.startswith("Bearer "):
        set_access_cookie(response, authorization.split(" ", 1)[1])
    user_dto, account_dto, role = service.get_me(user_id)
    return {
        "status": "success",
        "data": MeData(
            user=UserResponse.model_validate(user_dto),
            account=AccountResponse.model_validate(account_dto),
            role=role,
        ),
    }


@router.post("/logout")
def logout(
    response: Response,
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
    sessions: AuthSessionService = Depends(get_auth_session_service),
) -> dict:
    """Отозвать текущие token sessions и сбросить HttpOnly-cookie."""
    tokens = [access_token]
    if authorization and authorization.startswith("Bearer "):
        tokens.append(authorization.split(" ", 1)[1])
    for token in set(filter(None, tokens)):
        sessions.revoke_access_token(token)
    clear_access_cookie(response)
    return {"status": "success"}


@router.post("/forgot-password")
def forgot_password(
    body: ForgotPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Запросить сброс пароля."""
    service.request_password_reset(body.email)
    return {"message": "Если аккаунт с таким email существует, инструкция отправлена на почту."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    service: UserService = Depends(get_user_service),
) -> dict:
    """Сбросить пароль по токену."""
    reset_claims = verify_reset_token(body.token)
    if not reset_claims:
        raise ValidationError("Токен устарел или недействителен. Запросите восстановление заново.")
    user_id, token_id = reset_claims
    service.reset_password(user_id, token_id, body.new_password)
    return {"message": "Пароль успешно изменён."}


@router.put("/me")
def update_profile(
    body: UpdateProfileRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Обновить профиль."""
    dto = service.update_profile(user_id, body.full_name, body.phone)
    return {"status": "success", "data": UserResponse.model_validate(dto).model_dump()}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Сменить пароль."""
    service.change_password(user_id, body.current_password, body.new_password)
    clear_access_cookie(response)
    return {"message": "Пароль успешно изменён."}


@router.delete("/me")
def delete_account(
    body: DeleteAccountRequest,
    user_id: UUID = Depends(get_current_user_id),
    service: UserService = Depends(get_user_service),
) -> dict:
    """Удалить аккаунт (только владелец)."""
    service.delete_account(user_id, body.confirmation)
    return {"message": "Аккаунт удалён."}
