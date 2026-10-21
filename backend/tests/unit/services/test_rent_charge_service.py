"""Unit-тесты сервиса начислений."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.domain.entities import ContractEntity, RentChargeEntity
from app.services.dto.rent_charge_dto import RentChargeCreateDTO
from app.services.rent_charge_service import RentChargeService


@pytest.fixture
def mock_charge_repo():
    repo = Mock()
    repo.list_unpaid_for_contract_for_update.return_value = []
    return repo


@pytest.fixture
def mock_payment_repo():
    repo = Mock()
    repo.list_unlinked_for_contract_for_update.return_value = []
    repo.get_total_paid_for_charge.return_value = Decimal("0")
    return repo


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.get_by_id.return_value = ContractEntity(
        id=uuid4(), account_id=uuid4(), property_id=uuid4(),
        tenant_id=uuid4(), start_date=date(2026, 8, 1), end_date=date(2027, 7, 31),
        rent_amount=Decimal("50000"), currency="RUB", payment_day=5,
        status="active",
    )
    repo.get_by_id_for_update.return_value = repo.get_by_id.return_value
    return repo


@pytest.fixture
def service(mock_charge_repo, mock_payment_repo, mock_contract_repo):
    return RentChargeService(mock_charge_repo, mock_payment_repo, mock_contract_repo)


class TestCreateCharge:
    def test_success(self, service, mock_charge_repo):
        """Успешное создание начисления."""
        charge_id = uuid4()
        mock_charge_repo.create.return_value = RentChargeEntity(
            id=charge_id, account_id=uuid4(), contract_id=uuid4(),
            due_date=date(2026, 8, 5), period_start=date(2026, 8, 1),
            period_end=date(2026, 9, 1), amount=Decimal("50000"),
            currency="RUB", status="pending",
        )
        dto = RentChargeCreateDTO(
            contract_id=uuid4(),
            due_date=date(2026, 8, 5),
            period_start=date(2026, 8, 1),
            period_end=date(2026, 9, 1),
            amount=Decimal("50000"),
            currency="RUB",
        )
        result = service.create_charge(uuid4(), dto)
        assert result.amount == Decimal("50000")
        assert result.status == "pending"

    def test_contract_not_found(self, service, mock_contract_repo):
        """Контракт не найден."""
        mock_contract_repo.get_by_id.return_value = None
        mock_contract_repo.get_by_id_for_update.return_value = None
        dto = RentChargeCreateDTO(
            contract_id=uuid4(),
            due_date=date.today(),
            period_start=date.today(),
            period_end=date.today(),
            amount=Decimal("1000"),
        )
        with pytest.raises(NotFoundError):
            service.create_charge(uuid4(), dto)


class TestCreateChargesBatch:
    def test_generates_charges(self, service, mock_charge_repo):
        """Генерация начислений для контракта."""
        mock_charge_repo.create_if_absent.return_value = True
        mock_charge_repo.list_by_contract.return_value = [
            RentChargeEntity(
                id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                due_date=date(2026, 8, 5), period_start=date(2026, 8, 1),
                period_end=date(2026, 9, 1), amount=Decimal("50000"),
                currency="RUB", status="pending",
            ) for _ in range(12)
        ]
        result = service.create_charges_batch(uuid4(), uuid4())
        assert len(result) == 12

    def test_idempotent_when_charges_exist(self, service, mock_charge_repo):
        """Не создаёт дубли, если начисления уже есть."""
        existing = [
            RentChargeEntity(
                id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                due_date=date(2026, 8, 5), period_start=date(2026, 8, 1),
                period_end=date(2026, 9, 1), amount=Decimal("50000"),
                currency="RUB", status="pending",
            )
        ]
        mock_charge_repo.list_by_contract.return_value = existing
        result = service.create_charges_batch(uuid4(), uuid4())
        assert len(result) == 1
        mock_charge_repo.create.assert_not_called()

    def test_contract_not_found(self, service, mock_contract_repo):
        """Контракт не найден."""
        mock_contract_repo.get_by_id.return_value = None
        mock_contract_repo.get_by_id_for_update.return_value = None
        with pytest.raises(NotFoundError):
            service.create_charges_batch(uuid4(), uuid4())

class TestCreateChargesBatchMore:
    def test_contract_not_found_for_batch(self, service, mock_contract_repo):
        mock_contract_repo.get_by_id.return_value = None
        mock_contract_repo.get_by_id_for_update.return_value = None
        with pytest.raises(NotFoundError):
            service.create_charges_batch(uuid4(), uuid4())

    def test_creates_exact_count(self, service, mock_charge_repo):
        mock_charge_repo.list_by_contract.return_value = []
        mock_charge_repo.create_if_absent.return_value = True
        mock_charge_repo.list_by_contract.return_value = [
            RentChargeEntity(
                id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                due_date=date.today(), period_start=date.today(),
                period_end=date.today(), amount=Decimal("50000"),
                currency="RUB", status="pending",
            ) for _ in range(12)
        ]
        result = service.create_charges_batch(uuid4(), uuid4())
        assert len(result) == 12

class TestListCharges:
    def test_list_empty(self, service, mock_charge_repo):
        """Пустой список."""
        mock_charge_repo.list_by_account.return_value = []
        result = service.list_charges(uuid4())
        assert result == []

    def test_list_with_charges(self, service, mock_charge_repo, mock_payment_repo):
        """Список с начислениями и вычисленным статусом."""
        mock_charge_repo.list_by_account.return_value = [
            RentChargeEntity(
                id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
                due_date=date.today(), period_start=date.today(),
                period_end=date.today(), amount=Decimal("1000"),
                currency="RUB", status="pending",
            )
        ]
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
        result = service.list_charges(uuid4())
        assert len(result) == 1
