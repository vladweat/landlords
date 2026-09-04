"""Маршруты аккаунта и команды."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_account_service,
    get_current_account_id,
    require_permissions,
)
from app.api.v1.schemas.account_schema import (
    AccountResponse,
    AccountSingleResponse,
    AccountUpdateRequest,
    MemberCreateRequest,
    MemberListResponse,
    MemberResponse,
    MemberSingleResponse,
    MemberUpdateRequest,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.account_service import AccountService
from app.services.dto.membership_dto import (
    AccountUpdateDTO,
    MemberCreateDTO,
    MemberUpdateDTO,
)

router = APIRouter(prefix="/v1/account", tags=["Account"])


@router.get("", response_model=AccountSingleResponse)
def get_account(
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
) -> dict:
    """Получить настройки аккаунта."""
    dto = service.get_account(account_id)
    return {"status": "success", "data": AccountResponse.model_validate(dto)}


@router.patch("", response_model=AccountSingleResponse)
def update_account(
    body: AccountUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_ACCOUNT)),
) -> dict:
    """Обновить настройки аккаунта (owner)."""
    dto = service.update_account(
        account_id,
        AccountUpdateDTO(
            name=body.name,
            base_currency=body.base_currency,
            timezone=body.timezone,
        ),
    )
    return {"status": "success", "data": AccountResponse.model_validate(dto)}


@router.get("/members", response_model=MemberListResponse)
def list_members(
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> dict:
    """Список участников (owner)."""
    members = service.list_members(account_id)
    return {
        "status": "success",
        "data": [MemberResponse.model_validate(m) for m in members],
    }


@router.post("/members", response_model=MemberSingleResponse, status_code=201)
def create_member(
    body: MemberCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> dict:
    """Создать участника (owner)."""
    member = service.create_member(
        account_id,
        MemberCreateDTO(
            email=body.email,
            full_name=body.full_name,
            password=body.password,
            role=body.role,
        ),
    )
    return {"status": "success", "data": MemberResponse.model_validate(member)}


@router.patch("/members/{user_id}", response_model=MemberSingleResponse)
def update_member(
    user_id: UUID,
    body: MemberUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> dict:
    """Сменить роль участника (owner)."""
    member = service.update_member_role(
        account_id, user_id, MemberUpdateDTO(role=body.role)
    )
    return {"status": "success", "data": MemberResponse.model_validate(member)}


@router.delete("/members/{user_id}", status_code=204)
def remove_member(
    user_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: AccountService = Depends(get_account_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> None:
    """Удалить участника (owner)."""
    service.remove_member(account_id, user_id)
