"""Маршруты публичных квитанций (без JWT)."""

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_invoice_service, get_tenant_portal_service
from app.api.v1.schemas.invoice_schema import (
    CreateInvoiceClaimRequest,
    PublicInvoiceResponse,
    PublicInvoiceSingleResponse,
)
from app.api.v1.schemas.portal_schema import PaymentClaimResponse, PaymentClaimSingleResponse
from app.services.dto.portal_dto import CreatePaymentClaimDTO
from app.services.invoice_service import InvoiceService
from app.services.tenant_portal_service import TenantPortalService

router = APIRouter(prefix="/v1/public/invoices", tags=["Public Invoices"])


@router.get("/{token}", response_model=PublicInvoiceSingleResponse)
def get_public_invoice(
    token: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> dict:
    """Публичные данные квитанции по токену."""
    dto = service.get_public(token)
    return {
        "status": "success",
        "data": PublicInvoiceResponse.model_validate(dto),
    }


@router.get("/{token}/pdf")
def download_public_invoice_pdf(
    token: str,
    service: InvoiceService = Depends(get_invoice_service),
) -> Response:
    """Скачать PDF квитанции по публичному токену."""
    content, filename = service.get_public_pdf_bytes(token)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{token}/claim", response_model=PaymentClaimSingleResponse, status_code=201)
def create_invoice_claim(
    token: str,
    body: CreateInvoiceClaimRequest,
    service: TenantPortalService = Depends(get_tenant_portal_service),
) -> dict:
    """Заявка «я оплатил» со страницы квитанции (не создаёт payment)."""
    dto = service.create_claim_from_invoice(
        token,
        CreatePaymentClaimDTO(amount=body.amount, note=body.note),
    )
    return {
        "status": "success",
        "data": PaymentClaimResponse.model_validate(dto),
    }
