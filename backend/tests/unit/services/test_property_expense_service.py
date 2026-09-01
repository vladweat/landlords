"""Unit-тесты сервиса расходов по объектам."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import NotFoundError
from app.domain.entities import PropertyEntity, PropertyExpenseEntity
from app.services.dto.property_expense_dto import (
    PropertyExpenseCreateDTO,
    PropertyExpenseUpdateDTO,
)
from app.services.property_expense_service import PropertyExpenseService


@pytest.fixture
def mock_expense_repo():
    repo = Mock()
    repo.create.return_value = PropertyExpenseEntity(
        id=uuid4(),
        account_id=uuid4(),
        property_id=uuid4(),
        category="utilities",
        amount=Decimal("5000"),
        date_incurred=date.today(),
        currency="RUB",
    )
    return repo


@pytest.fixture
def mock_property_repo():
    repo = Mock()
    repo.get_by_id.return_value = PropertyEntity(
        id=uuid4(),
        account_id=uuid4(),
        city="Москва",
        street="Тестовая",
        house="1",
        type="apartment",
        size_m2=50.0,
        status="active",
    )
    return repo


@pytest.fixture
def service(mock_expense_repo, mock_property_repo):
    return PropertyExpenseService(mock_expense_repo, mock_property_repo)


class TestCreateExpense:
    def test_zero_amount_raises(self):
        with pytest.raises(PydanticValidationError):
            PropertyExpenseCreateDTO(
                property_id=uuid4(),
                category="utilities",
                amount=Decimal("0"),
                date_incurred=date.today(),
            )

    def test_invalid_category_raises(self):
        with pytest.raises(PydanticValidationError):
            PropertyExpenseCreateDTO(
                property_id=uuid4(),
                category="food",  # type: ignore[arg-type]
                amount=Decimal("100"),
                date_incurred=date.today(),
            )

    def test_property_not_found(self, service, mock_property_repo):
        mock_property_repo.get_by_id.return_value = None
        dto = PropertyExpenseCreateDTO(
            property_id=uuid4(),
            category="repair",
            amount=Decimal("10000"),
            date_incurred=date.today(),
        )
        with pytest.raises(NotFoundError):
            service.create_expense(uuid4(), dto)

    def test_success(self, service, mock_expense_repo):
        dto = PropertyExpenseCreateDTO(
            property_id=uuid4(),
            category="tax",
            amount=Decimal("15000"),
            date_incurred=date.today(),
            note="Имущественный налог",
        )
        result = service.create_expense(uuid4(), dto)
        assert mock_expense_repo.create.called
        assert result.amount == Decimal("5000")  # from mock return


class TestUpdateDeleteExpense:
    def test_update_not_found(self, service, mock_expense_repo):
        mock_expense_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.update_expense(
                uuid4(),
                uuid4(),
                PropertyExpenseUpdateDTO(amount=Decimal("1")),
            )

    def test_delete_not_found(self, service, mock_expense_repo):
        mock_expense_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete_expense(uuid4(), uuid4())

    def test_delete_success(self, service, mock_expense_repo):
        expense_id = uuid4()
        account_id = uuid4()
        mock_expense_repo.get_by_id.return_value = PropertyExpenseEntity(
            id=expense_id,
            account_id=account_id,
            property_id=uuid4(),
            category="other",
            amount=Decimal("100"),
            date_incurred=date.today(),
        )
        service.delete_expense(expense_id, account_id)
        mock_expense_repo.delete.assert_called_once_with(expense_id, account_id)
