"""Интеграционные тесты ручных платежей."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from threading import Barrier
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.contract_event_model import ContractEventModel
from app.db.models.payment_model import PaymentModel
from app.db.models.rent_charge_model import RentChargeModel
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.session import get_db_session
from app.db.tenant_context import set_tenant_context
from app.main import create_app
from app.services.email_service import EmailService
from app.services.ledger_service import LedgerService
from app.services.payment_service import PaymentService
from tests.integration.conftest import ALEMBIC_INI, property_payload


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


def _persist_charge(
    test_engine,
    *,
    account_id: str,
    contract_id: str,
    amount: str,
    offset_days: int,
) -> UUID:
    period_start = date.today() + timedelta(days=30 + offset_days)
    charge = RentChargeModel(
        id=uuid4(),
        account_id=UUID(account_id),
        contract_id=UUID(contract_id),
        due_date=period_start,
        period_start=period_start,
        period_end=period_start + timedelta(days=30),
        amount=Decimal(amount),
        currency="RUB",
        status="pending",
    )
    charge_id = charge.id
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, UUID(account_id))
        session.add(charge)
        session.commit()
    return charge_id


def _payment_audit_snapshot(test_engine, account_id: str, contract_id: str) -> dict:
    account_uuid = UUID(account_id)
    contract_uuid = UUID(contract_id)
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, account_uuid)
        payments = (
            session.query(PaymentModel)
            .filter_by(account_id=account_uuid, contract_id=contract_uuid)
            .all()
        )
        charges = (
            session.query(RentChargeModel)
            .filter_by(account_id=account_uuid, contract_id=contract_uuid)
            .all()
        )
        events = (
            session.query(ContractEventModel)
            .filter_by(
                account_id=account_uuid,
                contract_id=contract_uuid,
                event_type="payment",
            )
            .all()
        )
        ledger = LedgerService(
            ContractRepository(session),
            RentChargeRepository(session),
            PaymentRepository(session),
        ).get_ledger(contract_uuid, account_uuid)
        return {
            "received": sum((payment.amount for payment in payments), Decimal("0")),
            "allocated": sum(
                (payment.amount for payment in payments if payment.rent_charge_id),
                Decimal("0"),
            ),
            "advance": sum(
                (payment.amount for payment in payments if not payment.rent_charge_id),
                Decimal("0"),
            ),
            "expected": ledger.total_expected,
            "balance": ledger.outstanding_balance,
            "payments": {
                str(payment.id): {
                    "amount": payment.amount,
                    "rent_charge_id": str(payment.rent_charge_id)
                    if payment.rent_charge_id
                    else None,
                }
                for payment in payments
            },
            "events": [
                {
                    "amount": event.event_metadata["amount"],
                    "payment_id": event.event_metadata["payment_id"],
                }
                for event in events
            ],
        }


def _traceability_snapshot(test_engine, account_id: str, contract_id: str) -> dict:
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, UUID(account_id))
        params = {"account_id": account_id, "contract_id": contract_id}
        return {
            "receipts": session.execute(
                text(
                    "SELECT id, original_amount, source FROM payment_receipts "
                    "WHERE account_id = :account_id AND contract_id = :contract_id"
                ),
                params,
            ).all(),
            "allocation_targets": session.execute(
                text(
                    "SELECT id, original_amount, due_date, period_start, period_end "
                    "FROM payment_allocation_targets "
                    "WHERE account_id = :account_id AND contract_id = :contract_id"
                ),
                params,
            ).all(),
            "receipt_events": session.execute(
                text(
                    "SELECT receipt_id, event_type, amount_delta, resulting_date_paid, "
                    "resulting_method, resulting_note FROM payment_receipt_events "
                    "WHERE account_id = :account_id ORDER BY created_at, id"
                ),
                {"account_id": account_id},
            ).all(),
            "allocations": session.execute(
                text(
                    "SELECT receipt_id, rent_charge_id, event_type, amount, "
                    "reverses_event_id FROM payment_allocation_events "
                    "WHERE account_id = :account_id AND contract_id = :contract_id "
                    "ORDER BY created_at, id"
                ),
                params,
            ).all(),
            "payment_links": session.execute(
                text(
                    "SELECT id, receipt_id, allocation_event_id FROM payments "
                    "WHERE account_id = :account_id AND contract_id = :contract_id"
                ),
                params,
            ).all(),
            "contract_event_refs": session.execute(
                text(
                    "SELECT payment_receipt_id, event_metadata ->> 'payment_id' "
                    "FROM contract_events WHERE account_id = :account_id "
                    "AND contract_id = :contract_id AND event_type = 'payment'"
                ),
                params,
            ).all(),
        }


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
        test_engine,
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
            trace = _traceability_snapshot(test_engine, account_id, contract_id)
            assert trace["receipts"] == []
            assert trace["receipt_events"] == []
            assert trace["allocations"] == []
            assert _idempotency_record_count(db_session, account_id, key) == 0

            retried = api_client.post(
                "/v1/payments",
                headers={**headers, "Idempotency-Key": key},
                json=payload,
            )

        assert retried.status_code == 201
        assert _payment_and_event_counts(db_session, account_id, contract_id) == (1, 1)
        assert _idempotency_record_count(db_session, account_id, key) == 1

    def test_overpayment_then_partial_allocation_keeps_receipt_total_and_links(
        self, test_engine, client: TestClient, db_session
    ):
        headers = _register(client, f"receipt-partial-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers)
        db_session.commit()
        first_charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="1000.00",
            offset_days=0,
        )
        payload = _payment_payload(contract_id, "1500.00")
        payload["rent_charge_id"] = str(first_charge_id)
        response = client.post(
            "/v1/payments",
            headers=headers,
            json=payload,
        )

        assert response.status_code == 201
        assert len(response.json()["data"]["payments"]) == 2
        assert set(response.json()["data"]["payments"][0]) == {
            "id",
            "account_id",
            "contract_id",
            "rent_charge_id",
            "date_paid",
            "amount",
            "currency",
            "method",
            "note",
            "created_at",
            "updated_at",
        }
        db_session.commit()
        first = _payment_audit_snapshot(test_engine, account_id, contract_id)
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        assert first["received"] == Decimal("1500.00")
        assert first["allocated"] == Decimal("1000.00")
        assert first["advance"] == Decimal("500.00")
        assert len(trace["receipts"]) == 1
        receipt_id, original_amount, source = trace["receipts"][0]
        assert original_amount == Decimal("1500.00")
        assert source == "manual"
        assert {row[1] for row in trace["payment_links"]} == {receipt_id}
        assert trace["allocations"] == [
            (receipt_id, first_charge_id, "allocation", Decimal("1000.00"), None)
        ]
        assert trace["contract_event_refs"][0][0] == receipt_id

        second_charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="200.00",
            offset_days=30,
        )
        allocated = client.post(
            f"/v1/contracts/{contract_id}/allocate-advance", headers=headers
        )
        assert allocated.status_code == 200
        assert allocated.json()["data"]["allocated_count"] == 1
        db_session.commit()

        after_partial = _payment_audit_snapshot(test_engine, account_id, contract_id)
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        assert after_partial["received"] == Decimal("1500.00")
        assert after_partial["allocated"] == Decimal("1200.00")
        assert after_partial["advance"] == Decimal("300.00")
        assert trace["allocations"][-1] == (
            receipt_id,
            second_charge_id,
            "allocation",
            Decimal("200.00"),
            None,
        )
        assert all(row[1] == receipt_id for row in trace["payment_links"])

    def test_multi_charge_fifo_and_repeated_allocate_write_once(
        self, test_engine, client: TestClient, db_session
    ):
        headers = _register(client, f"receipt-fifo-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers)
        db_session.commit()
        created = client.post(
            "/v1/payments",
            headers=headers,
            json=_payment_payload(contract_id, "350.00"),
        )
        assert created.status_code == 201
        db_session.commit()
        receipt_id = _traceability_snapshot(test_engine, account_id, contract_id)[
            "receipts"
        ][0][0]

        first_charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="200.00",
            offset_days=0,
        )
        second_charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="300.00",
            offset_days=30,
        )
        later_charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="50.00",
            offset_days=60,
        )

        allocated = client.post(
            f"/v1/contracts/{contract_id}/allocate-advance", headers=headers
        )
        repeated = client.post(
            f"/v1/contracts/{contract_id}/allocate-advance", headers=headers
        )
        db_session.commit()
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        after = _payment_audit_snapshot(test_engine, account_id, contract_id)

        assert allocated.status_code == repeated.status_code == 200
        assert allocated.json()["data"]["allocated_count"] == 2
        assert repeated.json()["data"]["allocated_count"] == 0
        assert {
            (row[1], row[2], row[3], row[4]) for row in trace["allocations"]
        } == {
            (first_charge_id, "allocation", Decimal("200.00"), None),
            (second_charge_id, "allocation", Decimal("150.00"), None),
        }
        assert after["received"] == after["allocated"] == Decimal("350.00")
        assert after["advance"] == Decimal("0.00")
        assert after["balance"] == Decimal("200.00")
        assert later_charge_id not in {row[1] for row in trace["allocations"]}

    def test_payment_edit_and_delete_append_corrections_and_reversals(
        self, test_engine, client: TestClient, db_session
    ):
        headers = _register(client, f"receipt-corrections-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers)
        db_session.commit()
        charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="1000.00",
            offset_days=0,
        )
        _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="500.00",
            offset_days=30,
        )
        created = client.post(
            "/v1/payments",
            headers=headers,
            json=_payment_payload(contract_id, "1500.00"),
        )
        db_session.commit()
        linked_id = created.json()["data"]["payments"][0]["id"]
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        receipt_id = trace["receipts"][0][0]

        updated = client.put(
            f"/v1/payments/{linked_id}",
            headers=headers,
            json={"amount": "900.00", "date_paid": str(date.today() - timedelta(days=1))},
        )
        assert updated.status_code == 200
        db_session.commit()
        after_edit = _traceability_snapshot(test_engine, account_id, contract_id)
        after_edit_ledger = _payment_audit_snapshot(test_engine, account_id, contract_id)
        assert after_edit["receipts"] == [(receipt_id, Decimal("1500.00"), "manual")]
        assert after_edit["receipt_events"] == [
            (
                receipt_id,
                "correction",
                Decimal("-100.00"),
                date.today() - timedelta(days=1),
                "transfer",
                "Idempotency integration test",
            )
        ]
        assert sorted((row[2], row[3]) for row in after_edit["allocations"]) == [
            ("allocation", Decimal("500.00")),
            ("allocation", Decimal("900.00")),
            ("allocation", Decimal("1000.00")),
            ("reversal", Decimal("-1000.00")),
        ]
        assert after_edit_ledger["received"] == Decimal("1400.00")
        assert after_edit_ledger["allocated"] == Decimal("1400.00")
        assert after_edit_ledger["advance"] == Decimal("0.00")

        deleted = client.delete(f"/v1/payments/{linked_id}", headers=headers)
        assert deleted.status_code == 204
        db_session.commit()
        after_delete = _traceability_snapshot(test_engine, account_id, contract_id)
        final = _payment_audit_snapshot(test_engine, account_id, contract_id)
        assert after_delete["receipts"] == [(receipt_id, Decimal("1500.00"), "manual")]
        assert sorted((row[1], row[2]) for row in after_delete["receipt_events"]) == [
            ("cancellation", Decimal("-900.00")),
            ("correction", Decimal("-100.00")),
        ]
        assert ("reversal", Decimal("-900.00")) in {
            (row[2], row[3]) for row in after_delete["allocations"]
        }
        assert final["received"] == final["allocated"] == Decimal("500.00")
        assert final["advance"] == Decimal("0.00")
        assert final["balance"] == Decimal("1000.00")

        # Stable receipt FK remains resolvable after the projected payment row is deleted.
        assert after_delete["contract_event_refs"] == [(receipt_id, linked_id)]
        assert all(row[1] == receipt_id for row in after_delete["payment_links"])
        assert len(after_delete["receipts"]) == 1
        assert charge_id in {row[1] for row in after_delete["allocations"]}

        with sessionmaker(bind=test_engine)() as session:
            set_tenant_context(session, UUID(account_id))
            dangling_projection_refs = session.execute(
                text(
                    "SELECT count(*) FROM payments p "
                    "LEFT JOIN payment_receipts r "
                    "ON r.id = p.receipt_id AND r.account_id = p.account_id "
                    "WHERE p.account_id = :account_id AND p.receipt_id IS NOT NULL "
                    "AND r.id IS NULL"
                ),
                {"account_id": account_id},
            ).scalar_one()
            dangling_event_refs = session.execute(
                text(
                    "SELECT count(*) FROM contract_events e "
                    "LEFT JOIN payment_receipts r "
                    "ON r.id = e.payment_receipt_id AND r.account_id = e.account_id "
                    "WHERE e.account_id = :account_id "
                    "AND e.payment_receipt_id IS NOT NULL AND r.id IS NULL"
                ),
                {"account_id": account_id},
            ).scalar_one()
            assert dangling_projection_refs == 0
            assert dangling_event_refs == 0

    def test_payment_trace_tables_reject_direct_update_and_delete(
        self, test_engine, client: TestClient, db_session
    ):
        headers = _register(client, f"receipt-immutable-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers)
        db_session.commit()
        charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="100.00",
            offset_days=0,
        )
        payload = _payment_payload(contract_id, "100.00")
        payload["rent_charge_id"] = str(charge_id)
        created = client.post("/v1/payments", headers=headers, json=payload)
        assert created.status_code == 201
        db_session.commit()
        payment_id = created.json()["data"]["payments"][0]["id"]
        updated = client.put(
            f"/v1/payments/{payment_id}", headers=headers, json={"amount": "90.00"}
        )
        assert updated.status_code == 200
        db_session.commit()
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        receipt_id = trace["receipts"][0][0]

        admin_engine = create_engine(
            make_url(settings.MIGRATION_DATABASE_URL).set(database="landlords_test")
        )
        mutations = (
            ("UPDATE payment_receipts SET note = 'changed' WHERE id = :id", receipt_id),
            (
                "UPDATE payment_receipt_events SET amount_delta = 1.00 WHERE receipt_id = :id",
                receipt_id,
            ),
            (
                "UPDATE payment_allocation_targets SET original_amount = 1.00 WHERE id = :id",
                charge_id,
            ),
            (
                "UPDATE payment_allocation_events SET amount = 1.00 WHERE receipt_id = :id",
                receipt_id,
            ),
            ("DELETE FROM payment_receipts WHERE id = :id", receipt_id),
            ("DELETE FROM payment_receipt_events WHERE receipt_id = :id", receipt_id),
            ("DELETE FROM payment_allocation_targets WHERE id = :id", charge_id),
            ("DELETE FROM payment_allocation_events WHERE receipt_id = :id", receipt_id),
        )
        try:
            for statement, row_id in mutations:
                with pytest.raises(DBAPIError, match="append-only"):
                    with admin_engine.begin() as connection:
                        connection.execute(text(statement), {"id": row_id})
        finally:
            admin_engine.dispose()

    def test_payment_ids_remain_tenant_scoped_with_receipt_history(
        self, test_engine, client: TestClient, db_session
    ):
        headers_a = _register(client, f"payment-owner-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers_a)
        db_session.commit()
        created = client.post(
            "/v1/payments",
            headers=headers_a,
            json=_payment_payload(contract_id, "125.00"),
        )
        db_session.commit()
        payment_id = created.json()["data"]["payments"][0]["id"]
        headers_b = _register(client, f"payment-outsider-{uuid4().hex}@example.com")

        assert client.put(
            f"/v1/payments/{payment_id}", headers=headers_b, json={"amount": "1.00"}
        ).status_code == 404
        assert client.delete(f"/v1/payments/{payment_id}", headers=headers_b).status_code == 404
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        assert len(trace["receipts"]) == 1
        assert len(trace["payment_links"]) == 1

    def test_contract_termination_keeps_allocation_target_resolvable(
        self, test_engine, client: TestClient, db_session
    ):
        headers = _register(client, f"receipt-termination-{uuid4().hex}@example.com")
        contract_id, account_id = _create_contract(client, headers)
        db_session.commit()
        charge_id = _persist_charge(
            test_engine,
            account_id=account_id,
            contract_id=contract_id,
            amount="1000.00",
            offset_days=0,
        )
        payload = _payment_payload(contract_id, "1000.00")
        payload["rent_charge_id"] = str(charge_id)
        created = client.post("/v1/payments", headers=headers, json=payload)
        assert created.status_code == 201

        terminated = client.post(
            f"/v1/contracts/{contract_id}/terminate",
            headers=headers,
            json={
                "effective_date": str(date.today() + timedelta(days=30)),
                "termination_reason": "future charge removed",
                "generate_act": False,
            },
        )

        assert terminated.status_code == 200, terminated.text
        assert terminated.json()["data"]["charges_deleted"] == 1
        db_session.commit()
        trace = _traceability_snapshot(test_engine, account_id, contract_id)
        assert len(trace["receipts"]) == 1
        receipt_id = trace["receipts"][0][0]
        assert trace["allocation_targets"] == [
            (
                charge_id,
                Decimal("1000.00"),
                date.today() + timedelta(days=30),
                date.today() + timedelta(days=30),
                date.today() + timedelta(days=60),
            )
        ]
        allocations = trace["allocations"]
        assert [row[2:4] for row in allocations] == [
            ("allocation", Decimal("1000.00")),
            ("reversal", Decimal("-1000.00")),
        ]
        assert allocations[1][4] is not None
        assert all(row[0] == receipt_id and row[1] == charge_id for row in allocations)
        assert trace["contract_event_refs"] == [
            (receipt_id, created.json()["data"]["payments"][0]["id"])
        ]
        after_termination = _payment_audit_snapshot(
            test_engine, account_id, contract_id
        )
        assert after_termination["expected"] == Decimal("0.00")
        assert after_termination["received"] == Decimal("1000.00")
        assert after_termination["allocated"] == Decimal("0.00")
        assert after_termination["advance"] == Decimal("1000.00")
        assert after_termination["balance"] == Decimal("-1000.00")

        with sessionmaker(bind=test_engine)() as session:
            set_tenant_context(session, UUID(account_id))
            assert (
                session.execute(
                    text(
                        "SELECT count(*) FROM rent_charges "
                        "WHERE account_id = :account_id AND id = :charge_id"
                    ),
                    {"account_id": account_id, "charge_id": charge_id},
                ).scalar_one()
                == 0
            )
            allocation_events = session.execute(
                text(
                    "SELECT id, event_type, amount, reverses_event_id "
                    "FROM payment_allocation_events "
                    "WHERE account_id = :account_id AND receipt_id = :receipt_id "
                    "ORDER BY created_at, id"
                ),
                {"account_id": account_id, "receipt_id": receipt_id},
            ).all()
            assert allocation_events[1][3] == allocation_events[0][0]
            payment_link = session.execute(
                text(
                    "SELECT rent_charge_id, allocation_event_id FROM payments "
                    "WHERE account_id = :account_id"
                ),
                {"account_id": account_id},
            ).one()
            assert payment_link == (None, None)

    def test_traceability_downgrade_refuses_to_drop_recorded_history(
        self, test_engine, committed_client_factory
    ):
        with committed_client_factory() as api_client:
            headers = _register(
                api_client, f"payment-downgrade-{uuid4().hex}@example.com"
            )
            contract_id, account_id = _create_contract(api_client, headers)
            created = api_client.post(
                "/v1/payments",
                headers=headers,
                json=_payment_payload(contract_id, "125.00"),
            )
        assert created.status_code == 201

        alembic_cfg = Config(str(ALEMBIC_INI))
        alembic_cfg.set_main_option(
            "sqlalchemy.url",
            make_url(settings.MIGRATION_DATABASE_URL)
            .set(database="landlords_test")
            .render_as_string(hide_password=False)
            .replace("%", "%%"),
        )
        with patch.object(settings, "DB_NAME", "landlords_test"):
            with pytest.raises(RuntimeError, match="Cannot downgrade payment traceability"):
                command.downgrade(alembic_cfg, "04b5c6d7e8f9")

        with sessionmaker(bind=test_engine)() as session:
            set_tenant_context(session, UUID(account_id))
            current_revision = session.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
            receipt_count = session.execute(
                text("SELECT count(*) FROM payment_receipts")
            ).scalar_one()
        assert current_revision == "05c6d7e8f9a0"
        assert receipt_count == 1

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

    def test_receipt_split_allocation_edit_delete_and_duplicate_history(
        self, test_engine, committed_client_factory
    ):
        with committed_client_factory() as api_client:
            headers = _register(api_client, f"payment-history-{uuid4().hex}@example.com")
            contract_id, account_id = _create_contract(api_client, headers)
            first_charge_id = _persist_charge(
                test_engine,
                account_id=account_id,
                contract_id=contract_id,
                amount="1000.00",
                offset_days=0,
            )

            key = uuid4().hex
            payload = _payment_payload(contract_id, "1500.00")
            created = api_client.post(
                "/v1/payments",
                headers={**headers, "Idempotency-Key": key},
                json=payload,
            )
            assert created.status_code == 201
            initial_payment_ids = [
                row["id"] for row in created.json()["data"]["payments"]
            ]
            linked_payment_id, advance_payment_id = initial_payment_ids

            after_receipt = _payment_audit_snapshot(
                test_engine, account_id, contract_id
            )
            assert after_receipt["expected"] == Decimal("1000.00")
            assert after_receipt["received"] == Decimal("1500.00")
            assert after_receipt["allocated"] == Decimal("1000.00")
            assert after_receipt["advance"] == Decimal("500.00")
            assert after_receipt["balance"] == Decimal("-500.00")
            assert after_receipt["events"] == [
                {"amount": "1500.00", "payment_id": linked_payment_id}
            ]
            assert after_receipt["payments"][linked_payment_id]["amount"] == Decimal(
                "1000.00"
            )
            receipt_trace = _traceability_snapshot(test_engine, account_id, contract_id)
            receipt_id = receipt_trace["receipts"][0][0]
            assert receipt_trace["receipts"] == [
                (receipt_id, Decimal("1500.00"), "manual")
            ]
            assert {row[1] for row in receipt_trace["payment_links"]} == {receipt_id}
            assert receipt_trace["contract_event_refs"] == [(receipt_id, linked_payment_id)]

            second_charge_id = _persist_charge(
                test_engine,
                account_id=account_id,
                contract_id=contract_id,
                amount="500.00",
                offset_days=30,
            )
            barrier = Barrier(2)

            def allocate_concurrently() -> object:
                with committed_client_factory() as concurrent_client:
                    barrier.wait(timeout=30)
                    return concurrent_client.post(
                        f"/v1/contracts/{contract_id}/allocate-advance",
                        headers=headers,
                    )

            with ThreadPoolExecutor(max_workers=2) as executor:
                allocations = list(
                    executor.map(lambda _: allocate_concurrently(), range(2))
                )

            assert [response.status_code for response in allocations] == [200, 200]
            assert sorted(
                response.json()["data"]["allocated_count"] for response in allocations
            ) == [0, 1]

            after_allocate = _payment_audit_snapshot(
                test_engine, account_id, contract_id
            )
            assert after_allocate["expected"] == Decimal("1500.00")
            assert after_allocate["received"] == Decimal("1500.00")
            assert after_allocate["allocated"] == Decimal("1500.00")
            assert after_allocate["advance"] == Decimal("0.00")
            assert after_allocate["balance"] == Decimal("0.00")
            assert advance_payment_id not in after_allocate["payments"]
            new_allocation_ids = set(after_allocate["payments"]) - set(
                initial_payment_ids
            )
            assert len(new_allocation_ids) == 1
            assert after_allocate["events"] == [
                {"amount": "1500.00", "payment_id": linked_payment_id}
            ]
            allocation_trace = _traceability_snapshot(
                test_engine, account_id, contract_id
            )
            assert {
                (row[1], row[2], row[3], row[4])
                for row in allocation_trace["allocations"]
            } == {
                (first_charge_id, "allocation", Decimal("1000.00"), None),
                (second_charge_id, "allocation", Decimal("500.00"), None),
            }
            assert all(row[1] == receipt_id for row in allocation_trace["payment_links"])

            replay = api_client.post(
                "/v1/payments",
                headers={**headers, "Idempotency-Key": key},
                json=payload,
            )
            assert replay.status_code == 201
            assert replay.json() == created.json()
            assert advance_payment_id in {
                row["id"] for row in replay.json()["data"]["payments"]
            }
            assert advance_payment_id not in after_allocate["payments"]
            after_replay = _payment_audit_snapshot(test_engine, account_id, contract_id)
            assert after_replay["payments"] == after_allocate["payments"]
            assert after_replay["events"] == after_allocate["events"]

            updated = api_client.put(
                f"/v1/payments/{linked_payment_id}",
                headers=headers,
                json={"amount": "900.00"},
            )
            assert updated.status_code == 200
            after_update = _payment_audit_snapshot(test_engine, account_id, contract_id)
            assert after_update["received"] == Decimal("1400.00")
            assert after_update["allocated"] == Decimal("1400.00")
            assert after_update["balance"] == Decimal("100.00")
            assert after_update["events"] == [
                {"amount": "1500.00", "payment_id": linked_payment_id}
            ]
            assert after_update["payments"][linked_payment_id]["amount"] == Decimal(
                "900.00"
            )
            update_trace = _traceability_snapshot(test_engine, account_id, contract_id)
            assert update_trace["receipts"] == [
                (receipt_id, Decimal("1500.00"), "manual")
            ]
            assert update_trace["receipt_events"][0][2] == Decimal("-100.00")
            assert ("reversal", Decimal("-1000.00")) in {
                (row[2], row[3]) for row in update_trace["allocations"]
            }

            deleted = api_client.delete(
                f"/v1/payments/{linked_payment_id}", headers=headers
            )
            assert deleted.status_code == 204
            after_delete = _payment_audit_snapshot(test_engine, account_id, contract_id)
            assert after_delete["received"] == Decimal("500.00")
            assert after_delete["allocated"] == Decimal("500.00")
            assert after_delete["balance"] == Decimal("1000.00")
            assert after_delete["events"] == [
                {"amount": "1500.00", "payment_id": linked_payment_id}
            ]
            assert linked_payment_id not in after_delete["payments"]
            delete_trace = _traceability_snapshot(test_engine, account_id, contract_id)
            assert delete_trace["contract_event_refs"] == [(receipt_id, linked_payment_id)]
            assert delete_trace["receipts"] == [
                (receipt_id, Decimal("1500.00"), "manual")
            ]
            assert sorted(row[2] for row in delete_trace["receipt_events"]) == [
                Decimal("-900.00"),
                Decimal("-100.00"),
            ]

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
