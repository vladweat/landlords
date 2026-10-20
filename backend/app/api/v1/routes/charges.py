"""Маршруты для начислений."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_current_account_id,
    get_invoice_service,
    get_rent_charge_service,
    require_permissions,
)
from app.api.v1.schemas.invoice_schema import InvoiceResponse, InvoiceSingleResponse
from app.api.v1.schemas.rent_charge_schema import (
    RentChargeListResponse,
    RentChargeResponse,
    RentChargeSingleResponse,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.invoice_service import InvoiceService
from app.services.rent_charge_service import RentChargeService

router = APIRouter(prefix="/v1/charges", tags=["Charges"])


@router.get("", response_model=RentChargeListResponse)
def list_charges(
    account_id: UUID = Depends(get_current_account_id),
    service: RentChargeService = Depends(get_rent_charge_service),
) -> dict:
    """Получить список всех начислений."""
    charges = service.list_charges(account_id)
    return {
        "status": "success",
        "data": [RentChargeResponse.model_validate(c) for c in charges],
    }


@router.get("/contracts/{contract_id}/charges", response_model=RentChargeListResponse)
def list_charges_by_contract(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: RentChargeService = Depends(get_rent_charge_service),
) -> dict:
    """Получить начисления по контракту."""
    charges = service.list_charges_by_contract(contract_id, account_id)
    return {
        "status": "success",
        "data": [RentChargeResponse.model_validate(c) for c in charges],
    }


@router.post("/{charge_id}/invoice", response_model=InvoiceSingleResponse)
def create_or_refresh_invoice(
    charge_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: InvoiceService = Depends(get_invoice_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CHARGES)),
) -> dict:
    """Создать или обновить квитанцию по начислению."""
    dto = service.ensure_invoice(charge_id, account_id)
    return {
        "status": "success",
        "data": InvoiceResponse.model_validate(dto),
    }


@router.post("/{charge_id}/invoice/rotate-link", response_model=InvoiceSingleResponse)
def rotate_invoice_share_link(
    charge_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: InvoiceService = Depends(get_invoice_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CHARGES)),
) -> dict:
    """Перевыпустить публичную ссылку; прежний токен перестаёт работать."""
    dto = service.rotate_public_link(charge_id, account_id)
    return {
        "status": "success",
        "data": InvoiceResponse.model_validate(dto),
    }


@router.get("/{charge_id}/invoice", response_model=InvoiceSingleResponse)
def get_invoice_for_charge(
    charge_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: InvoiceService = Depends(get_invoice_service),
) -> dict:
    """Получить существующую квитанцию по начислению."""
    dto = service.get_by_charge(charge_id, account_id)
    return {
        "status": "success",
        "data": InvoiceResponse.model_validate(dto),
    }


@router.get("/{charge_id}", response_model=RentChargeSingleResponse)
def get_charge(
    charge_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: RentChargeService = Depends(get_rent_charge_service),
) -> dict:
    """Получить начисление по ID."""
    dto = service.get_charge(charge_id, account_id)
    return {
        "status": "success",
        "data": RentChargeResponse.model_validate(dto),
    }
