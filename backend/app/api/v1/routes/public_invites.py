"""Публичные маршруты принятия приглашения (без JWT)."""

from app.api.deps import get_invite_service
from app.api.v1.schemas.account_schema import (
    InviteAcceptRequest,
    InvitePreviewResponse,
    InvitePreviewSingleResponse,
)
from app.api.v1.schemas.user_schema import AuthData, AuthResponse, UserResponse
from app.services.dto.invite_dto import InviteAcceptDTO
from app.services.invite_service import InviteService
from fastapi import APIRouter, Depends, Header, Response

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


@router.post(
    "/{token}/accept",
    response_model=AuthResponse,
    response_model_exclude_none=True,
)
def accept_invite(
    token: str,
    body: InviteAcceptRequest,
    response: Response,
    return_bearer_token: bool = Header(False, alias="X-Return-Bearer-Token"),
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
        data=AuthData(
            token=jwt if return_bearer_token else None,
            user=UserResponse.model_validate(user),
        ),
    )
