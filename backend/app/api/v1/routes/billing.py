"""Маршруты SaaS-биллинга (ЮKassa)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.api.deps import (
    get_billing_service,
    get_current_account_id,
    require_permissions,
)
from app.api.v1.schemas.billing_schema import (
    BillingAccountResponse,
    BillingAccountSingleResponse,
    CheckoutResponse,
    CheckoutSingleResponse,
    ConfirmPaymentRequest,
    ConfirmPaymentResponse,
    ConfirmPaymentSingleResponse,
    WebhookAckResponse,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.billing_service import BillingService

router = APIRouter(prefix="/v1/billing", tags=["Billing"])


@router.post("/checkout", response_model=CheckoutSingleResponse)
def create_checkout(
    account_id: UUID = Depends(get_current_account_id),
    service: BillingService = Depends(get_billing_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_ACCOUNT)),
) -> dict:
    """Создать платёж Pro и получить confirmation_url."""
    data = service.create_checkout(account_id)
    return {"status": "success", "data": CheckoutResponse.model_validate(data)}


@router.post("/confirm", response_model=ConfirmPaymentSingleResponse)
def confirm_payment(
    body: ConfirmPaymentRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: BillingService = Depends(get_billing_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_ACCOUNT)),
) -> dict:
    """Подтвердить оплату после return с ЮKassa (работает без webhook)."""
    result = service.confirm_payment(account_id, body.payment_id)
    return {
        "status": "success",
        "data": ConfirmPaymentResponse(
            status=result.get("status", "ignored"),
            account_id=result.get("account_id"),
            reason=result.get("reason"),
        ),
    }


@router.post("/cancel", response_model=BillingAccountSingleResponse)
def cancel_subscription(
    account_id: UUID = Depends(get_current_account_id),
    service: BillingService = Depends(get_billing_service),
    _: MembershipEntity = Depends(require_permissions(Permission.MANAGE_ACCOUNT)),
) -> dict:
    """Отменить автоплатежи Pro."""
    account = service.cancel_subscription(account_id)
    period_end = (
        account.subscription_period_end.isoformat()
        if account.subscription_period_end
        else None
    )
    return {
        "status": "success",
        "data": BillingAccountResponse(
            id=str(account.id),
            plan=account.plan,
            subscription_status=account.subscription_status,
            subscription_period_end=period_end,
        ),
    }


@router.post("/webhooks/yookassa", response_model=WebhookAckResponse)
async def yookassa_webhook(
    request: Request,
    service: BillingService = Depends(get_billing_service),
) -> dict:
    """HTTP-уведомление ЮKassa (без JWT; статус берём из API)."""
    payload = await request.json()
    if not isinstance(payload, dict):
        payload = {}
    result = service.handle_webhook(payload)
    return {"status": "success", "data": result}
