"""Публичные маршруты принятия приглашения (без JWT)."""

from app.api.deps import get_invite_service
from app.api.v1.schemas.account_schema import (
    InviteAcceptRequest,
    InvitePreviewResponse,
    InvitePreviewSingleResponse,
)
from app.api.v1.schemas.user_schema import AuthResponse, UserResponse
from app.services.dto.invite_dto import InviteAcceptDTO
from app.services.invite_service import InviteService
from fastapi import APIRouter, Depends, Response

from app.core.cookies import set_access_cookie

router = APIRouter(prefix="/v1/public/invites", tags=["Public Invites"])


@router.get("/{token}", response_model=InvitePreviewSingleResponse)
def get_invite_preview(
    token: str,
    service: InviteService = Depends(get_invite_service),
) -> dict:
    """Публичные данные приглашения по токену."""
    dto = service.get_preview(token)
    return {
        "status": "success",
        "data": InvitePreviewResponse(**dto.model_dump()),
    }


@router.post("/{token}/accept", response_model=AuthResponse)
def accept_invite(
    token: str,
    body: InviteAcceptRequest,
    response: Response,
    service: InviteService = Depends(get_invite_service),
) -> AuthResponse:
    """Принять приглашение: задать пароль и войти."""
    user, jwt = service.accept(
        token,
        InviteAcceptDTO(password=body.password, full_name=body.full_name),
    )
    set_access_cookie(response, jwt)
    return AuthResponse(
        status="success",
        token=jwt,
        user=UserResponse.model_validate(user),
    )
