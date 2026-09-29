"""Маршруты аккаунта и команды."""

from uuid import UUID

from app.api.deps import (
    get_account_service,
    get_current_account_id,
    get_current_user_id,
    get_invite_service,
    require_permissions,
)
from app.api.v1.schemas.account_schema import (
    AccountResponse,
    AccountSingleResponse,
    AccountUpdateRequest,
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    InviteSingleResponse,
    MemberListResponse,
    MemberResponse,
    MemberSingleResponse,
    MemberUpdateRequest,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.account_service import AccountService
from app.services.dto.invite_dto import InviteCreateDTO
from app.services.dto.membership_dto import (
    AccountUpdateDTO,
    MemberUpdateDTO,
)
from app.services.invite_service import InviteService
from fastapi import APIRouter, Depends

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
            payment_details=body.payment_details,
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


@router.get("/invites", response_model=InviteListResponse)
def list_invites(
    account_id: UUID = Depends(get_current_account_id),
    service: InviteService = Depends(get_invite_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> dict:
    """Список активных приглашений (owner)."""
    invites = service.list_pending(account_id)
    return {
        "status": "success",
        "data": [InviteResponse.model_validate(i) for i in invites],
    }


@router.post("/invites", response_model=InviteSingleResponse, status_code=201)
def create_invite(
    body: InviteCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: InviteService = Depends(get_invite_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> dict:
    """Пригласить участника по ссылке (owner)."""
    invite = service.create_invite(
        account_id,
        user_id,
        InviteCreateDTO(email=body.email, full_name=body.full_name, role=body.role),
    )
    return {"status": "success", "data": InviteResponse.model_validate(invite)}


@router.delete("/invites/{invite_id}", status_code=204)
def revoke_invite(
    invite_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: InviteService = Depends(get_invite_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_TEAM)),
) -> None:
    """Отозвать приглашение (owner)."""
    service.revoke(account_id, invite_id)
