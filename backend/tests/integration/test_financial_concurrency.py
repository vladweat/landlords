"""PostgreSQL integration tests for financial idempotency and locking."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid4
from unittest.mock import Mock

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.exceptions import ValidationError
from app.services.email_service import EmailService
from app.db.models.account_model import AccountModel
from app.db.models.payment_model import PaymentModel
from app.db.models.rent_charge_model import RentChargeModel
from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.services.billing_service import BillingService
from app.services.dto.payment_dto import PaymentCreateDTO, PaymentUpdateDTO
from app.services.payment_allocation import allocate_unlinked_payments
from app.services.payment_service import PaymentService
from app.services.rent_charge_service import RentChargeService
from app.services.yookassa_client import YooKassaPaymentResult
from tests.integration.test_contracts_api import _create_property, _create_tenant


@pytest.fixture
def financial_auth_headers(client, monkeypatch):
    """Создать отдельный аккаунт для теста в общей интеграционной БД."""
    monkeypatch.setattr(EmailService, "send_welcome", lambda self, email, name: None)
    response = client.post(
        "/v1/auth/register",
        json={
            "email": f"financial-{uuid4().hex}@example.com",
            "password": "secret123",
            "full_name": "Financial Test User",
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _create_contract(client, headers, *, start=None, days=400):
    start = start or date.today() - timedelta(days=5)
    property_id = _create_property(client, headers, street=f"Money-{uuid4().hex[:8]}")
    tenant_id = _create_tenant(client, headers, name=f"Money-{uuid4().hex[:8]}")
    response = client.post(
        "/v1/contracts",
        headers=headers,
        json={
            "property_id": property_id,
            "tenant_id": tenant_id,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=days)).isoformat(),
            "rent_amount": "1000.00",
            "payment_day": 5,
        },
    )
    assert response.status_code == 201, response.text
    return UUID(response.json()["data"]["id"])


def _charge(session, contract_id, account_id, *, start, amount="1000.00"):
    charge = RentChargeModel(
        id=uuid4(),
        account_id=account_id,
        contract_id=contract_id,
        due_date=start,
        period_start=start,
        period_end=start + timedelta(days=30),
        amount=Decimal(amount),
        currency="RUB",
        status="pending",
    )
    session.add(charge)
    session.flush()
    return charge


def _payment_result(payment_id, account_id, period_end):
    return YooKassaPaymentResult(
        id=payment_id,
        status="succeeded",
        paid=True,
        amount_value="990.00",
        confirmation_url=None,
        payment_method_id="pm_test",
        metadata={
            "account_id": str(account_id),
            "plan": "pro",
            "renew": "1",
            "billing_period_end": period_end.isoformat(),
        },
        test=True,
    )


def test_renewal_retry_after_successful_provider_call_and_failed_commit(
    client, financial_auth_headers, test_engine, db_session
):
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    initial_end = datetime.now(timezone.utc) - timedelta(hours=1)
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with Session() as session:
        account = session.query(AccountModel).filter_by(id=account_id).one()
        account.plan = "pro"
        account.subscription_status = "active"
        account.subscription_period_end = initial_end
        account.yookassa_payment_method_id = "pm_test"
        session.commit()

    provider = Mock()
    provider.enabled = True
    payment = _payment_result("renewal-stable-period", account_id, initial_end)
    provider.find_renewal_payment_id.side_effect = [None, payment.id]
    provider.find_payment.return_value = payment
    provider.create_recurring_payment.return_value = payment
    commits = 0

    def fail_after_provider_id_once():
        nonlocal commits
        commits += 1
        if commits == 3:
            first_session.rollback()
            raise RuntimeError("simulated database commit failure")
        first_session.commit()

    first_session = Session()
    first = BillingService(AccountRepository(first_session), provider, commit=fail_after_provider_id_once)
    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        first.process_renewals(now=datetime.now(timezone.utc))
    first_key = provider.create_recurring_payment.call_args.kwargs["idempotence_key"]
    first_session.rollback()
    first_session.close()

    with Session() as session:
        account = session.query(AccountModel).filter_by(id=account_id).one()
        assert account.subscription_period_end == initial_end
        assert account.yookassa_renewal_idempotence_key == first_key
        assert account.yookassa_renewal_payment_id is None
        attempt_started_at = account.yookassa_renewal_started_at

    create_calls_before_retry = provider.create_recurring_payment.call_count
    expected_end = max(initial_end, datetime.now(timezone.utc)) + timedelta(days=30)
    with Session() as session:
        service = BillingService(AccountRepository(session), provider, commit=session.commit)
        result = service.process_renewals(now=datetime.now(timezone.utc))
        assert result["renewed"] == 1
    assert provider.create_recurring_payment.call_count == create_calls_before_retry
    provider.find_payment.assert_called_once_with(payment.id)
    assert provider.find_renewal_payment_id.call_count == 2
    assert provider.find_renewal_payment_id.call_args.kwargs == {
        "account_id": str(account_id),
        "billing_period_end": initial_end.isoformat(),
        "created_after": attempt_started_at,
    }

    with Session() as session:
        account = session.query(AccountModel).filter_by(id=account_id).one()
        assert abs((account.subscription_period_end - expected_end).total_seconds()) < 5
        assert account.yookassa_last_payment_id == payment.id
        assert account.yookassa_renewal_payment_id == payment.id
        assert account.yookassa_renewal_status == "succeeded"


def test_repeated_renewal_webhook_applies_period_once(
    client, financial_auth_headers, test_engine, db_session
):
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    initial_end = datetime.now(timezone.utc) - timedelta(hours=1)
    payment = _payment_result("webhook-renewal-once", account_id, initial_end)
    with test_engine.begin() as connection:
        connection.execute(
            AccountModel.__table__.update()
            .where(AccountModel.id == account_id)
            .values(
                plan="pro",
                subscription_status="active",
                subscription_period_end=initial_end,
                yookassa_payment_method_id="pm_test",
            )
        )
    provider = Mock()
    provider.enabled = True
    provider.find_payment.return_value = payment
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    for _ in range(2):
        session = Session()
        BillingService(AccountRepository(session), provider).handle_webhook(
            {"object": {"id": payment.id}}
        )
        session.commit()
        session.close()
    expected_end = max(initial_end, datetime.now(timezone.utc)) + timedelta(days=30)
    with test_engine.connect() as connection:
        row = connection.execute(
            AccountModel.__table__.select().where(AccountModel.id == account_id)
        ).one()
        assert abs((row.subscription_period_end - expected_end).total_seconds()) < 5
        assert row.yookassa_last_payment_id == payment.id


def test_parallel_charge_generation_creates_one_charge_per_period(
    client, financial_auth_headers, test_engine, db_session
):
    contract_id = _create_contract(client, financial_auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    barrier = Barrier(2)
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)

    def generate():
        with Session() as session:
            barrier.wait()
            service = RentChargeService(
                RentChargeRepository(session),
                PaymentRepository(session),
                ContractRepository(session),
            )
            result = service.create_charges_batch(account_id, contract_id)
            session.commit()
            return len(result)

    with ThreadPoolExecutor(max_workers=2) as pool:
        counts = list(pool.map(lambda _: generate(), range(2)))
    assert counts[0] == counts[1] > 0
    with Session() as session:
        periods = (
            session.query(RentChargeModel.period_start, RentChargeModel.period_end)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .all()
        )
        assert len(periods) == len(set(periods))


def test_parallel_payments_do_not_overpay_one_charge(
    client, financial_auth_headers, test_engine, db_session
):
    contract_id = _create_contract(client, financial_auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with Session() as session:
        charge = _charge(session, contract_id, account_id, start=date.today())
        charge_id = charge.id
        session.commit()
    barrier = Barrier(2)

    def pay():
        with Session() as session:
            barrier.wait()
            service = PaymentService(
                PaymentRepository(session),
                ContractRepository(session),
                RentChargeRepository(session),
            )
            result = service.create_payment(
                account_id,
                PaymentCreateDTO(
                    contract_id=contract_id,
                    rent_charge_id=charge_id,
                    date_paid=date.today(),
                    amount=Decimal("700.00"),
                    method="transfer",
                ),
            )
            session.commit()
            return result

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: pay(), range(2)))
    with Session() as session:
        linked_total = sum(
            (row.amount for row in session.query(PaymentModel).filter_by(rent_charge_id=charge_id)),
            Decimal("0"),
        )
        assert linked_total == Decimal("1000.00")
        charge = session.query(RentChargeModel).filter_by(id=charge_id).one()
        assert charge.status == "paid"


def test_parallel_advance_allocation_is_idempotent(
    client, financial_auth_headers, test_engine, db_session
):
    contract_id = _create_contract(client, financial_auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with Session() as session:
        first = _charge(session, contract_id, account_id, start=date.today())
        second = _charge(session, contract_id, account_id, start=date.today() + timedelta(days=30))
        session.add_all(
            [
                PaymentModel(
                    id=uuid4(), account_id=account_id, contract_id=contract_id,
                    rent_charge_id=first.id, date_paid=date.today(),
                    amount=Decimal("500.00"), currency="RUB", method="transfer",
                ),
                PaymentModel(
                    id=uuid4(), account_id=account_id, contract_id=contract_id,
                    rent_charge_id=None, date_paid=date.today(), amount=Decimal("750.00"),
                    currency="RUB", method="transfer",
                ),
            ]
        )
        session.commit()
        first_id, second_id = first.id, second.id
    barrier = Barrier(2)

    def allocate():
        with Session() as session:
            barrier.wait()
            charge_repo = RentChargeRepository(session)
            payment_repo = PaymentRepository(session)
            count = allocate_unlinked_payments(
                charge_repo,
                payment_repo,
                ContractRepository(session),
                contract_id,
                account_id,
            )
            session.commit()
            return count

    with ThreadPoolExecutor(max_workers=2) as pool:
        allocation_counts = list(pool.map(lambda _: allocate(), range(2)))
    assert sorted(allocation_counts) == [0, 2]
    with Session() as session:
        linked_first = session.query(PaymentModel).filter_by(rent_charge_id=first_id).all()
        linked_second = session.query(PaymentModel).filter_by(rent_charge_id=second_id).one()
        assert sum((row.amount for row in linked_first), Decimal("0")) == Decimal("1000.00")
        assert linked_second.amount == Decimal("250.00")
        assert session.query(PaymentModel).filter_by(
            contract_id=contract_id, rent_charge_id=None
        ).count() == 0


def test_payment_update_cannot_overfill_charge_and_delete_reallocates_advance(
    client, financial_auth_headers, test_engine, db_session
):
    contract_id = _create_contract(client, financial_auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with Session() as session:
        charge = _charge(session, contract_id, account_id, start=date.today())
        linked = PaymentModel(
            id=uuid4(), account_id=account_id, contract_id=contract_id,
            rent_charge_id=charge.id, date_paid=date.today(), amount=Decimal("600.00"),
            currency="RUB", method="transfer",
        )
        advance = PaymentModel(
            id=uuid4(), account_id=account_id, contract_id=contract_id,
            rent_charge_id=None, date_paid=date.today(), amount=Decimal("500.00"),
            currency="RUB", method="transfer",
        )
        session.add_all([linked, advance])
        session.commit()
        charge_id, linked_id = charge.id, linked.id

    with Session() as session:
        service = PaymentService(
            PaymentRepository(session),
            ContractRepository(session),
            RentChargeRepository(session),
        )
        with pytest.raises(ValidationError, match="Payment exceeds"):
            service.update_payment(
                linked_id,
                account_id,
                PaymentUpdateDTO(amount=Decimal("1100.00")),
            )
        session.rollback()

    with Session() as session:
        service = PaymentService(
            PaymentRepository(session),
            ContractRepository(session),
            RentChargeRepository(session),
        )
        service.delete_payment(linked_id, account_id)
        session.commit()

    with Session() as session:
        linked_total = session.query(PaymentModel).filter_by(
            rent_charge_id=charge_id
        ).with_entities(PaymentModel.amount).all()
        assert sum((amount for (amount,) in linked_total), Decimal("0")) == Decimal("500.00")
        assert session.query(PaymentModel).filter_by(
            contract_id=contract_id, rent_charge_id=None
        ).count() == 0


def test_financial_operation_rolls_back_after_mid_operation_failure(
    client, financial_auth_headers, test_engine, db_session
):
    contract_id = _create_contract(client, financial_auth_headers)
    account_id = UUID(client.get("/v1/auth/me", headers=financial_auth_headers).json()["data"]["account"]["id"])
    db_session.commit()
    Session = sessionmaker(bind=test_engine, expire_on_commit=False)
    with Session() as session:
        charge = _charge(session, contract_id, account_id, start=date.today())
        charge_id = charge.id
        session.commit()
    with Session() as session:
        class FailingEventRepository:
            def create(self, _event):
                raise RuntimeError("event write failed")

        service = PaymentService(
            PaymentRepository(session),
            ContractRepository(session),
            RentChargeRepository(session),
            FailingEventRepository(),
        )
        with pytest.raises(RuntimeError, match="event write failed"):
            service.create_payment(
                account_id,
                PaymentCreateDTO(
                    contract_id=contract_id,
                    rent_charge_id=charge_id,
                    date_paid=date.today(),
                    amount=Decimal("250.00"),
                    method="transfer",
                ),
            )
        session.rollback()
    with Session() as session:
        assert session.query(PaymentModel).filter_by(contract_id=contract_id).count() == 0
        assert session.query(RentChargeModel).filter_by(id=charge_id).one().status == "pending"
