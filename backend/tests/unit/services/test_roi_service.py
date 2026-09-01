"""Unit-тесты сервиса ROI."""

from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import PropertyEntity
from app.domain.pagination import PaginatedResult
from app.services.roi_service import RoiService


def _property(**kwargs) -> PropertyEntity:
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        city="Москва",
        street="Тестовая",
        house="1",
        type="apartment",
        size_m2=50.0,
        purchase_price=Decimal("5000000"),
        status="active",
    )
    defaults.update(kwargs)
    return PropertyEntity(**defaults)


@pytest.fixture
def mock_property_repo():
    repo = Mock()
    repo.get_by_id.return_value = _property()
    repo.list_by_account.return_value = PaginatedResult(
        items=[], total=0, page=1, per_page=20, pages=0
    )
    return repo


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.list_all_by_account.return_value = []
    repo.get_active_for_property.return_value = None
    return repo


@pytest.fixture
def mock_payment_repo():
    return Mock()


@pytest.fixture
def mock_expense_repo():
    repo = Mock()
    repo.get_total_for_property.return_value = Decimal("0")
    repo.list_by_account.return_value = []
    return repo


@pytest.fixture
def service(mock_property_repo, mock_contract_repo, mock_payment_repo, mock_expense_repo):
    return RoiService(
        mock_property_repo, mock_contract_repo, mock_payment_repo, mock_expense_repo
    )


class TestCalculateRoi:
    def test_no_purchase_price(self, service, mock_property_repo):
        mock_property_repo.get_by_id.return_value.purchase_price = None
        result = service.calculate_roi(uuid4(), uuid4())
        assert result["roi"] is None
        assert result["annual_income"] == Decimal("0")
        assert result["annual_expenses"] == Decimal("0")
        assert result["annual_profit"] == Decimal("0")

    def test_with_purchase_price_no_income(self, service):
        result = service.calculate_roi(uuid4(), uuid4())
        assert result["roi"] == 0.0
        assert result["payback_years"] is None
        assert result["annual_profit"] == Decimal("0")

    def test_expenses_reduce_profit(self, service, mock_expense_repo, mock_contract_repo):
        from app.domain.entities import ContractEntity
        from datetime import date

        mock_contract_repo.get_active_for_property.return_value = ContractEntity(
            id=uuid4(),
            account_id=uuid4(),
            property_id=uuid4(),
            tenant_id=uuid4(),
            start_date=date.today(),
            end_date=date.today(),
            rent_amount=Decimal("50000"),
            currency="RUB",
            payment_day=5,
            status="active",
        )
        mock_expense_repo.get_total_for_property.return_value = Decimal("120000")

        result = service.calculate_roi(uuid4(), uuid4())
        # income fallback 50000*12=600000, expenses 120000 → profit 480000
        assert result["annual_income"] == Decimal("600000")
        assert result["annual_expenses"] == Decimal("120000")
        assert result["annual_profit"] == Decimal("480000")
        assert result["roi"] == 9.6  # 480000/5000000*100


class TestCalculatePortfolioRoi:
    def test_empty_portfolio(self, service):
        result = service.calculate_portfolio_roi(uuid4())
        assert result["portfolio_roi"] is None
        assert result["properties_with_roi"] == 0

    def test_portfolio_with_prices(self, service, mock_property_repo, mock_contract_repo, mock_payment_repo):
        prop1 = _property(purchase_price=Decimal("5000000"))
        prop2 = _property(purchase_price=Decimal("3000000"))
        mock_property_repo.list_by_account.return_value = PaginatedResult(
            items=[prop1, prop2], total=2, page=1, per_page=20, pages=1,
        )
        mock_payment_repo.list_by_contract.return_value = []
        mock_contract_repo.get_active_for_property.return_value = None

        result = service.calculate_portfolio_roi(uuid4())
        assert result["properties_with_roi"] == 2
        assert result["portfolio_roi"] == 0.0
