"""Unit-тесты сервиса кредитного рейтинга."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import PaymentEntity, RentChargeEntity
from app.services.credit_score_service import CreditScoreService


@pytest.fixture
def mock_payment_repo():
    return Mock()


@pytest.fixture
def mock_charge_repo():
    return Mock()


@pytest.fixture
def service(mock_payment_repo, mock_charge_repo):
    return CreditScoreService(mock_payment_repo, mock_charge_repo)


class TestCalculate:
    def test_no_data_less_than_3_payments(self, service, mock_payment_repo):
        mock_payment_repo.get_by_tenant.return_value = [Mock(), Mock()]  # 2 платежа
        result = service.calculate(uuid4(), uuid4())
        assert result["score"] == "no_data"

    def test_reliable(self, service, mock_payment_repo, mock_charge_repo):
        charge = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            due_date=date.today() + timedelta(days=10),
            period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="paid",
        )
        mock_charge_repo.get_by_id.return_value = charge

        payments = [
            PaymentEntity(id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                         rent_charge_id=charge.id, date_paid=date.today(),
                         amount=Decimal("1000"), currency="RUB", method="bank")
            for _ in range(5)
        ]
        mock_payment_repo.get_by_tenant.return_value = payments
        result = service.calculate(uuid4(), uuid4())
        assert result["score"] == "reliable"
        assert result["metrics"]["total_payments"] == 5

    def test_problematic_all_late(self, service, mock_payment_repo, mock_charge_repo):
        charge = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            due_date=date.today() - timedelta(days=60),
            period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="overdue",
        )
        mock_charge_repo.get_by_id.return_value = charge

        payments = [
            PaymentEntity(id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                         rent_charge_id=charge.id, date_paid=date.today(),
                         amount=Decimal("1000"), currency="RUB", method="bank")
            for _ in range(5)
        ]
        mock_payment_repo.get_by_tenant.return_value = payments
        result = service.calculate(uuid4(), uuid4())
        assert result["score"] == "problematic"
        assert result["metrics"]["severe_late_count"] == 5