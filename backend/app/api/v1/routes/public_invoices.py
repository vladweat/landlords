"""Маршруты публичных квитанций (без JWT)."""

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_invoice_service
from app.api.v1.schemas.invoice_schema import (
    PublicInvoiceResponse,
    PublicInvoiceSingleResponse,
)
from app.services.invoice_service import InvoiceService

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
