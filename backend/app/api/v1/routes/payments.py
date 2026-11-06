"""Маршруты для платежей."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.mappers import to_dto
from app.api.deps import (
    get_current_account_id,
    get_payment_idempotency_service,
    get_payment_service,
    require_permissions,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
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
from app.services.payment_idempotency_service import PaymentIdempotencyService
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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
    idempotency_service: PaymentIdempotencyService = Depends(
        get_payment_idempotency_service
    ),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
) -> dict:
    """Создать платёж (при автораспределении — все split-строки)."""
    reservation = None
    if idempotency_key is not None:
        reservation = idempotency_service.reserve_or_replay(
            account_id=account_id,
            key=idempotency_key,
            request=body,
        )
        if reservation.is_replay:
            assert reservation.response_snapshot is not None
            return reservation.response_snapshot

    dto = to_dto(body, PaymentCreateDTO)
    result = service.create_payment(account_id, dto)
    response = {
        "status": "success",
        "data": PaymentCreateData(
            payments=[PaymentResponse.model_validate(p) for p in result.payments],
            total_amount=result.total_amount,
        ),
    }
    if reservation is not None:
        assert reservation.record_id is not None
        snapshot = PaymentCreateResponse.model_validate(response).model_dump(mode="json")
        idempotency_service.complete(
            account_id=account_id,
            record_id=reservation.record_id,
            response_snapshot=snapshot,
        )
    return response


@router.put("/{payment_id}", response_model=PaymentSingleResponse)
def update_payment(
    payment_id: UUID,
    body: PaymentUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
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
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
) -> None:
    """Удалить платёж."""
    service.delete_payment(payment_id, account_id)
