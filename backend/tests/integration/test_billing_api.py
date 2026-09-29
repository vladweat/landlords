"""Интеграционные тесты SaaS-биллинга."""

from unittest.mock import patch

from fastapi.testclient import TestClient

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
