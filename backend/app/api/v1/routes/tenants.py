"""Маршруты для арендаторов."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_tenant_service, get_credit_score_service
from app.api.v1.schemas.tenant_schema import (
    TenantCreateRequest,
    TenantListResponse,
    TenantResponse,
    TenantSingleResponse,
    TenantUpdateRequest,
)
from app.services.tenant_service import TenantService
from app.services.credit_score_service import CreditScoreService
from app.api.pagination import PaginationParams

router = APIRouter(prefix="/v1/tenants", tags=["Tenants"])


@router.get("")
def list_tenants(
    account_id: UUID = Depends(get_current_account_id),
    service: TenantService = Depends(get_tenant_service),
    pagination: PaginationParams = Depends(),
    search: str | None = None,
    include_score: bool = False,
    score_service: CreditScoreService = Depends(get_credit_score_service),
) -> dict:
    """Получить список арендаторов."""
    result = service.list_tenants(
        account_id, page=pagination.page, per_page=pagination.per_page, search=search,
    )
    items = []
    for e in result.items:
        item = TenantResponse.model_validate(e).model_dump()
        if include_score:
            item["score"] = score_service.calculate(e.id, account_id)
        items.append(item)

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages,
        },
    }


@router.post("", response_model=TenantSingleResponse, status_code=201)
def create_tenant(
    body: TenantCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantService = Depends(get_tenant_service),
) -> dict:
    """Создать арендатора."""
    dto = service.create_tenant(account_id, body)
    return {"status": "success", "data": TenantResponse.model_validate(dto).model_dump()}


@router.get("/{tenant_id}")
def get_tenant(
    tenant_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantService = Depends(get_tenant_service),
) -> dict:
    """Получить арендатора по ID."""
    dto = service.get_tenant(tenant_id, account_id)
    return {"status": "success", "data": TenantResponse.model_validate(dto).model_dump()}


@router.put("/{tenant_id}")
def update_tenant(
    tenant_id: UUID,
    body: TenantUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantService = Depends(get_tenant_service),
) -> dict:
    """Обновить арендатора."""
    dto = service.update_tenant(tenant_id, account_id, body)
    return {"status": "success", "data": TenantResponse.model_validate(dto).model_dump()}


@router.delete("/{tenant_id}", status_code=204)
def delete_tenant(
    tenant_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantService = Depends(get_tenant_service),
) -> None:
    """Удалить арендатора."""
    service.delete_tenant(tenant_id, account_id)


@router.get("/{tenant_id}/score")
def get_tenant_score(
    tenant_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: CreditScoreService = Depends(get_credit_score_service),
) -> dict:
    result = service.calculate(tenant_id, account_id)
    return {"status": "success", "data": result}