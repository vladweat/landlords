"""Unit-тесты сервиса контрактов."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import ContractEntity
from app.services.contract_service import ContractService
from app.services.dto.contract_dto import ContractCreateDTO, ContractUpdateDTO


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.get_active_by_property.return_value = None
    repo.get_by_id_for_update.side_effect = lambda *args: repo.get_by_id(*args)
    return repo


@pytest.fixture
def contract_service(mock_contract_repo):
    property_repo = Mock()
    property_repo.get_by_id.return_value = object()
    tenant_repo = Mock()
    tenant_repo.get_by_id.return_value = object()
    return ContractService(
        mock_contract_repo, property_repo=property_repo, tenant_repo=tenant_repo
    )


class TestCreateContract:
    def test_create_success(self, contract_service, mock_contract_repo):
        """Успешное создание контракта."""
        account_id = uuid4()
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=365)

        mock_contract_repo.create.return_value = ContractEntity(
            id=uuid4(), account_id=account_id, property_id=uuid4(), tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("50000"),
            currency="RUB", payment_day=5, status="draft",
        )

        dto = ContractCreateDTO(
            property_id=uuid4(), tenant_id=uuid4(),
            start_date=start, end_date=end,
            rent_amount=Decimal("50000"), payment_day=5,
        )

        result = contract_service.create_contract(account_id, dto)
        assert result.rent_amount == Decimal("50000")
        assert result.status == "draft"

    def test_create_draft_allowed_with_active_contract(
        self, contract_service, mock_contract_repo
    ):
        """Draft можно создать даже если на объекте уже есть active/overdue."""
        account_id = uuid4()
        property_id = uuid4()
        start = date.today() + timedelta(days=30)
        end = start + timedelta(days=365)

        mock_contract_repo.get_active_by_property.return_value = ContractEntity(
            id=uuid4(), account_id=account_id, property_id=property_id, tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("50000"),
            currency="RUB", payment_day=5, status="active",
        )
        mock_contract_repo.create.return_value = ContractEntity(
            id=uuid4(), account_id=account_id, property_id=property_id, tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("50000"),
            currency="RUB", payment_day=5, status="draft",
        )

        dto = ContractCreateDTO(
            property_id=property_id, tenant_id=uuid4(),
            start_date=start, end_date=end,
            rent_amount=Decimal("50000"), payment_day=5,
        )

        result = contract_service.create_contract(account_id, dto)
        assert result.status == "draft"
        mock_contract_repo.create.assert_called_once()
        mock_contract_repo.get_active_by_property.assert_not_called()

    def test_create_invalid_dates(self, contract_service, mock_contract_repo):
        """Ошибка: start_date не раньше end_date."""
        account_id = uuid4()
        mock_contract_repo.get_active_by_property.return_value = None

        dto = ContractCreateDTO(
            property_id=uuid4(), tenant_id=uuid4(),
            start_date=date(2027, 8, 31), end_date=date(2020, 1, 1),
            rent_amount=Decimal("50000"), payment_day=5,
        )

        with pytest.raises(ValidationError):
            contract_service.create_contract(account_id, dto)


class TestGetContract:
    def test_get_existing(self, contract_service, mock_contract_repo):
        """Получить существующий контракт."""
        account_id = uuid4()
        contract_id = uuid4()
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=365)

        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=account_id, property_id=uuid4(), tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("50000"),
            currency="RUB", payment_day=5, status="active",
        )

        result = contract_service.get_contract(contract_id, account_id)
        assert result.id == contract_id

    def test_get_not_found(self, contract_service, mock_contract_repo):
        """Контракт не найден."""
        mock_contract_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            contract_service.get_contract(uuid4(), uuid4())


class TestUpdateContract:
    def test_activate_generates_charges(self, contract_service, mock_contract_repo):
        """Активация с auto_generate_charges вызывает задачу."""
        account_id = uuid4()
        contract_id = uuid4()
        start = date.today() + timedelta(days=1)
        end = start + timedelta(days=365)

        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=account_id, property_id=uuid4(), tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="draft", auto_generate_charges=True,
        )
        mock_contract_repo.get_active_by_property.return_value = None
        mock_contract_repo.update.return_value = ContractEntity(
            id=contract_id, account_id=account_id, property_id=uuid4(), tenant_id=uuid4(),
            start_date=start, end_date=end, rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active", auto_generate_charges=True,
        )

        # Мокаем charge_repo
        contract_service.charge_repo = Mock()

        with patch("app.celery_app.celery_app.send_task") as mock_task:
            dto = ContractUpdateDTO(status="active")
            result = contract_service.update_contract(contract_id, account_id, dto)
            assert result.status == "active"
            mock_task.assert_called_once()
