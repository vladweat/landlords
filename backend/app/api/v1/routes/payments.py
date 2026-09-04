"""Маршруты для платежей."""

from uuid import UUID

from fastapi import APIRouter, Depends
from app.api.mappers import to_dto
from app.api.deps import get_current_account_id, get_payment_service
from app.api.v1.schemas.payment_schema import (
    PaymentCreateData,
    PaymentCreateRequest,
    PaymentCreateResponse,
    PaymentListResponse,
    PaymentResponse,
    PaymentSingleResponse,
    PaymentUpdateRequest,
)
from app.services.dto.payment_dto import PaymentCreateDTO, PaymentUpdateDTO
from app.services.payment_service import PaymentService
from app.api.responses import success_response, success_list_response

router = APIRouter(prefix="/v1/payments", tags=["Payments"])


@router.get("", response_model=PaymentListResponse)
def list_payments(
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    """Получить список всех платежей."""
    payments = service.list_payments(account_id)
    return {
        "status": "success",
        "data": [PaymentResponse.model_validate(p) for p in payments],
    }


@router.get("/contracts/{contract_id}/payments", response_model=PaymentListResponse)
def list_payments_by_contract(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    """Получить платежи по контракту."""
    payments = service.list_payments_by_contract(contract_id, account_id)
    return {
        "status": "success",
        "data": [PaymentResponse.model_validate(p) for p in payments],
    }


@router.post("", response_model=PaymentCreateResponse, status_code=201)
def create_payment(
    body: PaymentCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    """Создать платёж (при автораспределении — все split-строки)."""
    dto = to_dto(body, PaymentCreateDTO)
    result = service.create_payment(account_id, dto)
    return {
        "status": "success",
        "data": PaymentCreateData(
            payments=[PaymentResponse.model_validate(p) for p in result.payments],
            total_amount=result.total_amount,
        ),
    }


@router.put("/{payment_id}", response_model=PaymentSingleResponse)
def update_payment(
    payment_id: UUID,
    body: PaymentUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
) -> dict:
    """Обновить платёж."""
    # dto = PaymentUpdateDTO(
    #     date_paid=body.date_paid,
    #     amount=body.amount,
    #     method=body.method,
    #     note=body.note,
    # )
    
    dto = to_dto(body, PaymentUpdateDTO)
    updated = service.update_payment(payment_id, account_id, dto)
    return {
        "status": "success",
        "data": PaymentResponse.model_validate(updated),
    }


@router.delete("/{payment_id}", status_code=204)
def delete_payment(
    payment_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
) -> None:
    """Удалить платёж."""
    service.delete_payment(payment_id, account_id)