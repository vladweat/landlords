"""Маршруты шаблонов договоров."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_contract_template_service,
    get_current_account_id,
    require_permissions,
)
from app.api.v1.schemas.contract_template_schema import (
    ContractTemplateCreateRequest,
    ContractTemplateResponse,
    ContractTemplateUpdateRequest,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.contract_template_service import ContractTemplateService
from app.services.dto.contract_template_dto import (
    ContractTemplateCreateDTO,
    ContractTemplateUpdateDTO,
)

router = APIRouter(prefix="/v1/contract-templates", tags=["Contract Templates"])


@router.get("")
def list_templates(
    account_id: UUID = Depends(get_current_account_id),
    service: ContractTemplateService = Depends(get_contract_template_service),
) -> dict:
    """Список шаблонов аккаунта (с авто-seed дефолтов)."""
    items = service.list_templates(account_id)
    return {
        "status": "success",
        "data": {
            "items": [ContractTemplateResponse.model_validate(i) for i in items],
            "placeholders": service.placeholder_hints(),
        },
    }


@router.get("/{template_id}")
def get_template(
    template_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractTemplateService = Depends(get_contract_template_service),
) -> dict:
    """Получить шаблон."""
    item = service.get_template(template_id, account_id)
    return {
        "status": "success",
        "data": ContractTemplateResponse.model_validate(item),
    }


@router.post("")
def create_template(
    body: ContractTemplateCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractTemplateService = Depends(get_contract_template_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Создать шаблон."""
    dto = ContractTemplateCreateDTO.model_validate(body.model_dump())
    item = service.create_template(account_id, dto)
    return {
        "status": "success",
        "data": ContractTemplateResponse.model_validate(item),
    }


@router.put("/{template_id}")
def update_template(
    template_id: UUID,
    body: ContractTemplateUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractTemplateService = Depends(get_contract_template_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Обновить шаблон."""
    dto = ContractTemplateUpdateDTO.model_validate(
        body.model_dump(exclude_unset=True)
    )
    item = service.update_template(template_id, account_id, dto)
    return {
        "status": "success",
        "data": ContractTemplateResponse.model_validate(item),
    }


@router.delete("/{template_id}")
def delete_template(
    template_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractTemplateService = Depends(get_contract_template_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Удалить шаблон."""
    service.delete_template(template_id, account_id)
    return {"status": "success", "data": {"deleted": True}}
