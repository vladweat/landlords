"""CRM-маршруты заявок «я оплатил»."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_current_account_id,
    get_current_user_id,
    get_tenant_portal_service,
    require_permissions,
)
from app.api.v1.schemas.portal_schema import PaymentClaimResponse, PaymentClaimSingleResponse
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.tenant_portal_service import TenantPortalService

router = APIRouter(prefix="/v1/claims", tags=["Payment Claims"])


@router.post("/{claim_id}/dismiss", response_model=PaymentClaimSingleResponse)
def dismiss_claim(
    claim_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: TenantPortalService = Depends(get_tenant_portal_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
) -> dict:
    """Отклонить заявку арендатора."""
    dto = service.dismiss_claim(claim_id, account_id, user_id)
    return {
        "status": "success",
        "data": PaymentClaimResponse.model_validate(dto),
    }


@router.post("/{claim_id}/confirm", response_model=PaymentClaimSingleResponse)
def confirm_claim(
    claim_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: TenantPortalService = Depends(get_tenant_portal_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
) -> dict:
    """Подтвердить заявку и провести платёж в ledger."""
    dto = service.confirm_claim(claim_id, account_id, user_id)
    return {
        "status": "success",
        "data": PaymentClaimResponse.model_validate(dto),
    }
