from contextlib import ExitStack
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy.orm import sessionmaker

from app import demo_seed
from app.db.models.contract_event_model import ContractEventModel
from app.db.models.contract_model import ContractModel
from app.db.models.payment_model import PaymentModel
from app.db.models.payment_receipt_model import PaymentReceiptModel
from app.db.models.property_model import PropertyModel
from app.db.models.rent_charge_model import RentChargeModel
from app.db.models.tenant_model import TenantModel
from app.db.tenant_context import set_tenant_context
from app.services.ledger_service import LedgerService
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.services.email_service import EmailService
from app.services.yookassa_client import YooKassaClient


DEMO_PARTIAL_PAYMENT_NOTE = "Демо: частичная оплата"


class JanuaryFirst(date):
    @classmethod
    def today(cls) -> "JanuaryFirst":
        return cls(2026, 1, 1)


def _run_demo(monkeypatch, test_engine, email: str, full_name: str, capsys) -> UUID:
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    monkeypatch.setattr(
        demo_seed,
        "settings",
        SimpleNamespace(APP_ENV="demo", DB_NAME="landlords_demo"),
        raising=False,
    )
    monkeypatch.setattr(demo_seed, "SessionLocal", session_factory)
    monkeypatch.setattr(demo_seed, "date", JanuaryFirst)
    monkeypatch.setattr(EmailService, "send_welcome", lambda *args, **kwargs: None)

    provider_mocks = []
    with ExitStack() as stack:
        for method_name in (
            "__init__",
            "create_checkout_payment",
            "create_recurring_payment",
            "find_payment",
            "find_renewal_payment_id",
        ):
            provider_mocks.append(
                stack.enter_context(
                    patch.object(
                        YooKassaClient,
                        method_name,
                        autospec=True,
                        side_effect=AssertionError("demo seed attempted provider I/O"),
                    )
                )
            )

        assert demo_seed.run_seed_demo(
            email=email,
            password="SyntheticDemoPassword123!",
            full_name=full_name,
        ) == 0
        output = capsys.readouterr().out

    assert all(not provider_mock.called for provider_mock in provider_mocks)
    account_lines = [line for line in output.splitlines() if line.startswith("account_id=")]
    assert len(account_lines) == 1
    return UUID(account_lines[0].partition("=")[2])


def _counts(test_engine, account_id: UUID) -> tuple[int, ...]:
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, account_id)
        return tuple(
            session.query(model).filter_by(account_id=account_id).count()
            for model in (
                PropertyModel,
                TenantModel,
                ContractModel,
                RentChargeModel,
                PaymentModel,
                PaymentReceiptModel,
                ContractEventModel,
            )
        )


def test_seed_demo_replay_is_idempotent_and_builds_partial_ledger_without_provider_calls(
    monkeypatch, test_engine, capsys
) -> None:
    email = f"demo-{uuid4().hex}@example.com"
    account_id = _run_demo(monkeypatch, test_engine, email, "Synthetic Demo", capsys)
    counts_before = _counts(test_engine, account_id)

    repeated_account_id = _run_demo(
        monkeypatch, test_engine, email, "Synthetic Demo", capsys
    )

    assert repeated_account_id == account_id
    assert _counts(test_engine, account_id) == counts_before

    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, account_id)
        property_model = (
            session.query(PropertyModel)
            .filter_by(account_id=account_id, street="Арбат", house="15")
            .one()
        )
        tenant = (
            session.query(TenantModel)
            .filter_by(account_id=account_id, email="anna.smirnova@example.com")
            .one()
        )
        contract = (
            session.query(ContractModel)
            .filter_by(
                account_id=account_id,
                property_id=property_model.id,
                tenant_id=tenant.id,
            )
            .one()
        )
        charge = (
            session.query(RentChargeModel)
            .filter_by(account_id=account_id, contract_id=contract.id)
            .order_by(RentChargeModel.due_date)
            .first()
        )
        payment = (
            session.query(PaymentModel)
            .filter_by(
                account_id=account_id,
                contract_id=contract.id,
                note=DEMO_PARTIAL_PAYMENT_NOTE,
            )
            .one()
        )
        ledger = LedgerService(
            ContractRepository(session),
            RentChargeRepository(session),
            PaymentRepository(session),
        ).get_ledger(contract.id, account_id)

        assert property_model.account_id == tenant.account_id == contract.account_id
        assert charge is not None
        assert payment.rent_charge_id == charge.id
        assert charge.amount == Decimal("75000.00")
        assert payment.amount == Decimal("37500.00")
        assert ledger.total_expected == sum(
            (
                row.amount
                for row in session.query(RentChargeModel).filter_by(
                    account_id=account_id, contract_id=contract.id
                )
            ),
            Decimal("0"),
        )
        assert ledger.total_paid == sum(
            (
                row.amount
                for row in session.query(PaymentModel).filter_by(
                    account_id=account_id, contract_id=contract.id
                )
            ),
            Decimal("0"),
        )
        assert ledger.outstanding_balance == ledger.total_expected - ledger.total_paid


def test_demo_seed_data_isolated_between_accounts(monkeypatch, test_engine, capsys) -> None:
    account_a = _run_demo(
        monkeypatch,
        test_engine,
        f"demo-a-{uuid4().hex}@example.com",
        "Synthetic A",
        capsys,
    )
    account_b = _run_demo(
        monkeypatch,
        test_engine,
        f"demo-b-{uuid4().hex}@example.com",
        "Synthetic B",
        capsys,
    )

    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    with session_factory() as session:
        set_tenant_context(session, account_a)
        assert session.query(PropertyModel).filter_by(account_id=account_a).count() == 4
        assert session.query(PropertyModel).filter_by(account_id=account_b).count() == 0

        set_tenant_context(session, account_b)
        assert session.query(PropertyModel).filter_by(account_id=account_b).count() == 4
        assert session.query(PropertyModel).filter_by(account_id=account_a).count() == 0
