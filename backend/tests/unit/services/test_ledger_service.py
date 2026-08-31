"""Unit-тесты сервиса ledger."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import ContractEntity, PaymentEntity, RentChargeEntity
from app.services.ledger_service import LedgerService


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.get_by_id.return_value = ContractEntity(
        id=uuid4(), account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=335),
        rent_amount=Decimal("50000"), currency="RUB", payment_day=5, status="active",
    )
    return repo


@pytest.fixture
def mock_charge_repo():
    repo = Mock()
    repo.list_by_contract.return_value = [
        RentChargeEntity(id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                        due_date=date.today() - timedelta(days=10),
                        period_start=date.today() - timedelta(days=40),
                        period_end=date.today() - timedelta(days=10),
                        amount=Decimal("50000"), currency="RUB", status="overdue"),
        RentChargeEntity(id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                        due_date=date.today() + timedelta(days=20),
                        period_start=date.today() - timedelta(days=10),
                        period_end=date.today() + timedelta(days=20),
                        amount=Decimal("50000"), currency="RUB", status="pending"),
    ]
    return repo


@pytest.fixture
def mock_payment_repo():
    repo = Mock()
    repo.list_by_contract.return_value = [
        PaymentEntity(id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                     date_paid=date.today() - timedelta(days=5),
                     amount=Decimal("30000"), currency="RUB", method="bank"),
    ]
    return repo


@pytest.fixture
def service(mock_contract_repo, mock_charge_repo, mock_payment_repo):
    return LedgerService(mock_contract_repo, mock_charge_repo, mock_payment_repo)


class TestGetLedger:
    def test_returns_summary(self, service):
        result = service.get_ledger(uuid4(), uuid4())
        assert result.total_expected == Decimal("100000")
        assert result.total_paid == Decimal("30000")
        assert result.outstanding_balance == Decimal("70000")
        assert result.overdue_days == 10

    def test_returns_lines(self, service):
        result = service.get_ledger(uuid4(), uuid4())
        assert len(result.lines) == 3  # 2 charges + 1 payment

    def test_contract_not_found(self, service, mock_contract_repo):
        mock_contract_repo.get_by_id.return_value = None
        with pytest.raises(Exception):
            service.get_ledger(uuid4(), uuid4())