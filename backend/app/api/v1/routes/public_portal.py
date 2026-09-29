"""Публичные маршруты портала арендатора (без JWT)."""

from fastapi import APIRouter, Depends

from app.api.deps import get_tenant_portal_service
from app.api.v1.schemas.portal_schema import (
    CreatePaymentClaimRequest,
    PaymentClaimResponse,
    PaymentClaimSingleResponse,
    PublicPortalResponse,
    PublicPortalSingleResponse,
)
from app.services.dto.portal_dto import CreatePaymentClaimDTO
from app.services.tenant_portal_service import TenantPortalService

router = APIRouter(prefix="/v1/public/portal", tags=["Public Portal"])


@router.get("/{token}", response_model=PublicPortalSingleResponse)
def get_public_portal(
    token: str,
    service: TenantPortalService = Depends(get_tenant_portal_service),
) -> dict:
    """Публичные данные портала договора по magic link."""
    dto = service.get_public(token)
    return {
        "status": "success",
        "data": PublicPortalResponse.model_validate(dto),
    }


@router.post("/{token}/claim", response_model=PaymentClaimSingleResponse, status_code=201)
def create_public_claim(
    token: str,
    body: CreatePaymentClaimRequest,
    service: TenantPortalService = Depends(get_tenant_portal_service),
) -> dict:
    """Заявка арендатора «я оплатил» (не создаёт платёж в ledger)."""
    dto = service.create_claim(
        token,
        CreatePaymentClaimDTO(
            charge_id=body.charge_id,
            amount=body.amount,
            note=body.note,
        ),
    )
    return {
        "status": "success",
        "data": PaymentClaimResponse.model_validate(dto),
    }
