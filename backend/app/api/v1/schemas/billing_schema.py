"""Pydantic-схемы для SaaS-биллинга."""

from pydantic import BaseModel, Field


class CheckoutResponse(BaseModel):
    """Ссылка на оплату ЮKassa."""

    confirmation_url: str
    payment_id: str


class CheckoutSingleResponse(BaseModel):
    status: str = "success"
    data: CheckoutResponse


class ConfirmPaymentRequest(BaseModel):
    """Подтверждение оплаты после возврата с ЮKassa."""

    payment_id: str = Field(min_length=1)


class ConfirmPaymentResponse(BaseModel):
    status: str
    account_id: str | None = None
    reason: str | None = None


class ConfirmPaymentSingleResponse(BaseModel):
    status: str = "success"
    data: ConfirmPaymentResponse


class BillingAccountResponse(BaseModel):
    """Аккаунт после cancel."""

    id: str
    plan: str
    subscription_status: str
    subscription_period_end: str | None = None


class BillingAccountSingleResponse(BaseModel):
    status: str = "success"
    data: BillingAccountResponse


class WebhookAckResponse(BaseModel):
    status: str = "success"
    data: dict
