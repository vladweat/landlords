"""Маршруты для начислений."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_rent_charge_service
from app.api.v1.schemas.rent_charge_schema import (
    RentChargeListResponse,
    RentChargeResponse,
    RentChargeSingleResponse,
)
from app.services.rent_charge_service import RentChargeService
from app.api.responses import success_response, success_list_response

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