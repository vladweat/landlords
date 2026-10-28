"""Интеграционные тесты SaaS-биллинга."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import settings
from app.db.models.account_model import AccountModel
from app.services.yookassa_client import YooKassaPaymentResult


def test_checkout_without_keys(client: TestClient, auth_headers):
    resp = client.post("/v1/billing/checkout", headers=auth_headers)
    assert resp.status_code == 422
    assert "не настроена" in resp.json()["message"].lower()


def test_subscription_includes_billing_fields(client: TestClient, auth_headers):
    resp = client.get("/v1/account/subscription", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["subscription_status"] == "none"
    assert data["billing_enabled"] is False
    assert data["write_blocked"] is False
    assert data["plans_catalog"][1]["price_rub_monthly"] == 990


def test_webhook_with_mock(client: TestClient, auth_headers):
    me = client.get("/v1/auth/me", headers=auth_headers)
    account_id = me.json()["data"]["account"]["id"]

    payment = YooKassaPaymentResult(
        id="pay_int_1",
        status="succeeded",
        paid=True,
        amount_value="990.00",
        confirmation_url=None,
        payment_method_id="pm_int_1",
        metadata={"account_id": account_id, "plan": "pro"},
        test=True,
    )

    with patch(
        "app.services.yookassa_client.YooKassaClient.find_payment",
        return_value=payment,
    ):
        resp = client.post(
            "/v1/billing/webhooks/yookassa",
            json={"event": "payment.succeeded", "object": {"id": "pay_int_1"}},
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "applied"

    sub = client.get("/v1/account/subscription", headers=auth_headers)
    assert sub.json()["data"]["plan"] == "pro"
    assert sub.json()["data"]["subscription_status"] == "active"


def test_cancel_subscription(client: TestClient, auth_headers):
    me = client.get("/v1/auth/me", headers=auth_headers)
    account_id = me.json()["data"]["account"]["id"]
    payment = YooKassaPaymentResult(
        id="pay_cancel_1",
        status="succeeded",
        paid=True,
        amount_value="990.00",
        confirmation_url=None,
        payment_method_id="pm_c1",
        metadata={"account_id": account_id, "plan": "pro"},
        test=True,
    )
    with patch(
        "app.services.yookassa_client.YooKassaClient.find_payment",
        return_value=payment,
    ):
        client.post(
            "/v1/billing/webhooks/yookassa",
            json={"object": {"id": "pay_cancel_1"}},
        )

    resp = client.post("/v1/billing/cancel", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["subscription_status"] in ("canceled", "none")


def test_confirm_rejects_payment_owned_by_another_account(client, auth_headers, db_session):
    other = client.post("/v1/auth/register", json={
        "email": "billing-other@test.com", "password": "secret123", "full_name": "Other"
    }).json()
    other_headers = {"Authorization": f"Bearer {other['data']['token']}"}
    current_id = client.get("/v1/auth/me", headers=auth_headers).json()["data"]["account"]["id"]
    other_id = client.get("/v1/auth/me", headers=other_headers).json()["data"]["account"]["id"]
    payment = YooKassaPaymentResult(
        id="payment-owned-by-other", status="succeeded", paid=True,
        amount_value="990.00", confirmation_url=None, payment_method_id="pm_other",
        metadata={"account_id": other_id, "plan": "pro"}, test=True,
    )

    with patch.object(settings, "YOOKASSA_SHOP_ID", "test-shop"), \
         patch.object(settings, "YOOKASSA_SECRET_KEY", "test-secret"), \
         patch("app.services.yookassa_client.YooKassaClient.find_payment", return_value=payment):
        response = client.post("/v1/billing/confirm", headers=auth_headers,
            json={"payment_id": payment.id})

    assert response.status_code == 422
    db_session.expire_all()
    assert db_session.query(AccountModel).filter_by(id=current_id).one().plan == "free"
    assert db_session.query(AccountModel).filter_by(id=other_id).one().plan == "free"
