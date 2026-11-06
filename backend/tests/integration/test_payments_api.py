"""Интеграционные тесты ручных платежей."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.contract_event_model import ContractEventModel
from app.db.models.payment_model import PaymentModel
from app.db.session import get_db_session
from app.db.tenant_context import set_tenant_context
from app.main import create_app
from app.services.email_service import EmailService
from app.services.payment_service import PaymentService
from tests.integration.conftest import property_payload


def _register(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/v1/auth/register",
        json={"email": email, "password": "secret123", "full_name": "Payment User"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['data']['token']}"}


def _create_contract(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
    suffix = uuid4().hex[:10]
    property_response = client.post(
        "/v1/properties",
        headers=headers,
        json=property_payload(street=f"Idempotency {suffix}"),
    )
    assert property_response.status_code == 201
    tenant_response = client.post(
        "/v1/tenants", headers=headers, json={"full_name": f"Tenant {suffix}"}
    )
    assert tenant_response.status_code == 201

    start_date = date.today() + timedelta(days=30)
    response = client.post(
        "/v1/contracts",
        headers=headers,
        json={
            "property_id": property_response.json()["data"]["id"],
            "tenant_id": tenant_response.json()["data"]["id"],
            "start_date": str(start_date),
            "end_date": str(start_date + timedelta(days=365)),
            "rent_amount": "10000.00",
            "payment_day": 5,
        },
    )
    assert response.status_code == 201
    data = response.json()["data"]
    return data["id"], data["account_id"]


def _payment_payload(contract_id: str, amount: str = "125.00") -> dict:
    return {
        "contract_id": contract_id,
        "date_paid": str(date.today()),
        "amount": amount,
        "method": "transfer",
        "note": "Idempotency integration test",
    }


def _payment_and_event_counts(db_session, account_id: str, contract_id: str) -> tuple[int, int]:
    account_uuid = UUID(account_id)
    contract_uuid = UUID(contract_id)
    set_tenant_context(db_session, account_uuid)
    payments = (
        db_session.query(PaymentModel)
        .filter_by(account_id=account_uuid, contract_id=contract_uuid)
        .count()
    )
    events = (
        db_session.query(ContractEventModel)
        .filter_by(account_id=account_uuid, contract_id=contract_uuid)
        .count()
    )
    return payments, events


def _idempotency_record_count(db_session, account_id: str, key: str) -> int:
    set_tenant_context(db_session, UUID(account_id))
    return db_session.execute(
        text(
            "SELECT count(*) FROM public.payment_idempotency_records "
            "WHERE account_id = :account_id "
            "AND operation_scope = 'payments:create' AND key = :key"
        ),
        {"account_id": account_id, "key": key},
    ).scalar_one()


@pytest.fixture
def committed_client_factory(test_engine, monkeypatch):
    """Клиенты с отдельной транзакцией на HTTP-запрос для конкурентных тестов."""
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def skip_smtp(
        service: EmailService, to: str, subject: str, body_text: str
    ) -> None:
        return None

    monkeypatch.setattr(EmailService, "_send_smtp", skip_smtp)

    def create_client(*, raise_server_exceptions: bool = True) -> TestClient:
        app = create_app()

        def override_get_db():
            session = session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        app.dependency_overrides[get_db_session] = override_get_db
        return TestClient(
            app,
            headers={
                "Origin": settings.FRONTEND_URL,
                "X-Return-Bearer-Token": "true",
            },
            raise_server_exceptions=raise_server_exceptions,
        )

    return create_client


class TestPayments:
    def test_list_empty(self, client: TestClient, auth_headers):
        response = client.get("/v1/payments", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json()["data"], list)

    def test_no_token(self, client: TestClient):
        response = client.get("/v1/payments")
        assert response.status_code in (401, 403, 422)

    def test_same_key_and_canonical_payload_replays_original_response(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id, account_id = _create_contract(client, auth_headers)
        key = uuid4().hex
        payload = _payment_payload(contract_id)

        first = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=payload,
        )
        reordered_payload = dict(reversed(list(payload.items())))
        replay = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=reordered_payload,
        )

        assert first.status_code == 201
        assert replay.status_code == 201
        assert replay.json() == first.json()
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)
        assert _idempotency_record_count(db_session, account_id, key) == 1

    def test_same_key_with_different_payload_returns_conflict_without_mutation(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id, account_id = _create_contract(client, auth_headers)
        key = uuid4().hex
        first = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=_payment_payload(contract_id, "125.00"),
        )
        mismatch = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=_payment_payload(contract_id, "126.00"),
        )

        assert first.status_code == 201
        assert mismatch.status_code == 409
        assert mismatch.json()["status"] == "error"
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)

    def test_same_key_is_scoped_to_authenticated_account(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_a, account_a = _create_contract(client, auth_headers)
        headers_b = _register(client, f"payment-b-{uuid4().hex}@example.com")
        contract_b, account_b = _create_contract(client, headers_b)
        key = uuid4().hex

        response_a = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=_payment_payload(contract_a, "125.00"),
        )
        response_b = client.post(
            "/v1/payments",
            headers={**headers_b, "Idempotency-Key": key},
            json=_payment_payload(contract_b, "250.00"),
        )

        assert response_a.status_code == response_b.status_code == 201
        payment_a = response_a.json()["data"]["payments"][0]["id"]
        payment_b = response_b.json()["data"]["payments"][0]["id"]
        assert payment_a != payment_b
        assert _payment_and_event_counts(db_session, account_a, contract_a) == (1, 1)
        assert _payment_and_event_counts(db_session, account_b, contract_b) == (1, 1)
        assert _idempotency_record_count(db_session, account_a, key) == 1
        assert _idempotency_record_count(db_session, account_b, key) == 1

    def test_parallel_same_key_requests_create_one_business_effect(
        self, committed_client_factory, db_session
    ):
        with committed_client_factory() as setup_client:
            headers = _register(
                setup_client, f"payment-parallel-{uuid4().hex}@example.com"
            )
            contract_id, account_id = _create_contract(setup_client, headers)

        key = uuid4().hex
        payload = _payment_payload(contract_id)
        barrier = Barrier(2)

        def submit() -> object:
            with committed_client_factory() as concurrent_client:
                barrier.wait(timeout=30)
                return concurrent_client.post(
                    "/v1/payments",
                    headers={**headers, "Idempotency-Key": key},
                    json=payload,
                )

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: submit(), range(2)))

        assert [response.status_code for response in responses] == [201, 201]
        assert responses[0].json() == responses[1].json()
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)
        assert _idempotency_record_count(db_session, account_id, key) == 1

    def test_failed_request_rolls_back_reservation_payments_and_event(
        self,
        committed_client_factory,
        db_session,
        monkeypatch,
    ):
        with committed_client_factory(raise_server_exceptions=False) as api_client:
            headers = _register(api_client, f"payment-rollback-{uuid4().hex}@example.com")
            contract_id, account_id = _create_contract(api_client, headers)
            key = uuid4().hex
            payload = _payment_payload(contract_id)
            create_payment = PaymentService.create_payment

            def create_then_fail(service, *args, **kwargs):
                create_payment(service, *args, **kwargs)
                raise RuntimeError("fail after payment and event flush")

            with monkeypatch.context() as patcher:
                patcher.setattr(PaymentService, "create_payment", create_then_fail)
                failed = api_client.post(
                    "/v1/payments",
                    headers={**headers, "Idempotency-Key": key},
                    json=payload,
                )

            assert failed.status_code == 500
            assert failed.json() == {"status": "error", "message": "Internal server error"}
            assert _payment_and_event_counts(db_session, account_id, contract_id) == (0, 0)
            assert _idempotency_record_count(db_session, account_id, key) == 0

            retried = api_client.post(
                "/v1/payments",
                headers={**headers, "Idempotency-Key": key},
                json=payload,
            )

        assert retried.status_code == 201
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)
        assert _idempotency_record_count(db_session, account_id, key) == 1

    def test_replay_after_unrelated_payment_returns_original_snapshot(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id, account_id = _create_contract(client, auth_headers)
        key = uuid4().hex
        first = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=_payment_payload(contract_id, "125.00"),
        )
        unrelated = client.post(
            "/v1/payments",
            headers=auth_headers,
            json=_payment_payload(contract_id, "75.00"),
        )
        replay = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=_payment_payload(contract_id, "125.00"),
        )

        assert first.status_code == unrelated.status_code == replay.status_code == 201
        assert replay.json() == first.json()
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (2, 2)

    def test_expired_key_can_be_reused_and_is_replaced(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id, account_id = _create_contract(client, auth_headers)
        key = uuid4().hex
        payload = _payment_payload(contract_id)
        first = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=payload,
        )
        set_tenant_context(db_session, UUID(account_id))
        db_session.execute(
            text(
                "UPDATE public.payment_idempotency_records "
                "SET expires_at = CURRENT_TIMESTAMP - interval '1 second' "
                "WHERE account_id = :account_id "
                "AND operation_scope = 'payments:create' AND key = :key"
            ),
            {"account_id": account_id, "key": key},
        )

        reused = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=payload,
        )

        assert first.status_code == reused.status_code == 201
        assert reused.json() != first.json()
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (2, 2)
        assert _idempotency_record_count(db_session, account_id, key) == 1

    def test_key_length_is_bounded(self, client: TestClient, auth_headers):
        contract_id, _ = _create_contract(client, auth_headers)
        response = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": "k" * 256},
            json=_payment_payload(contract_id),
        )

        assert response.status_code == 422
        assert response.json()["status"] == "error"

    def test_old_client_without_key_still_creates_payment(
        self, client: TestClient, auth_headers, db_session
    ):
        contract_id, account_id = _create_contract(client, auth_headers)
        response = client.post(
            "/v1/payments", headers=auth_headers, json=_payment_payload(contract_id)
        )

        assert response.status_code == 201
        assert response.json()["status"] == "success"
        assert len(response.json()["data"]["payments"]) == 1
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)

    def test_replay_still_requires_authenticated_membership(
        self, client: TestClient, auth_headers
    ):
        contract_id, _ = _create_contract(client, auth_headers)
        key = uuid4().hex
        payload = _payment_payload(contract_id)
        created = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=payload,
        )
        with TestClient(
            client.app,
            headers={
                "Origin": settings.FRONTEND_URL,
                "X-Return-Bearer-Token": "true",
            },
        ) as anonymous_client:
            unauthenticated = anonymous_client.post(
                "/v1/payments", headers={"Idempotency-Key": key}, json=payload
            )
        replay = client.post(
            "/v1/payments",
            headers={**auth_headers, "Idempotency-Key": key},
            json=payload,
        )

        assert created.status_code == replay.status_code == 201
        assert unauthenticated.status_code == 401
        assert unauthenticated.json()["status"] == "error"
        assert replay.json() == created.json()
