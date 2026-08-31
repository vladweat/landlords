"""Unit-тесты сервиса ROI."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import PropertyEntity
from app.services.roi_service import RoiService
from app.domain.pagination import PaginatedResult

@pytest.fixture
def mock_property_repo():
    repo = Mock()
    repo.get_by_id.return_value = PropertyEntity(
        id=uuid4(), account_id=uuid4(), address="ул. Тестовая",
        type="apartment", size_m2=50.0, purchase_price=Decimal("5000000"), status="active",
    )
    repo.list_all_by_account.return_value = []
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
def service(mock_property_repo, mock_contract_repo, mock_payment_repo):
    return RoiService(mock_property_repo, mock_contract_repo, mock_payment_repo)


class TestCalculateRoi:
    def test_no_purchase_price(self, service, mock_property_repo):
        mock_property_repo.get_by_id.return_value.purchase_price = None
        result = service.calculate_roi(uuid4(), uuid4())
        assert result["roi"] is None
        assert result["annual_income"] == Decimal("0")

    def test_with_purchase_price_no_income(self, service):
        result = service.calculate_roi(uuid4(), uuid4())
        assert result["roi"] == 0.0
        assert result["payback_years"] is None


class TestCalculatePortfolioRoi:
    def test_empty_portfolio(self, service):
        result = service.calculate_portfolio_roi(uuid4())
        assert result["portfolio_roi"] is None
        assert result["properties_with_roi"] == 0
        
class TestCalculatePortfolioRoiMore:
    def test_portfolio_with_prices(self, service, mock_property_repo, mock_contract_repo, mock_payment_repo):
        from app.domain.pagination import PaginatedResult
        prop1 = PropertyEntity(
            id=uuid4(), account_id=uuid4(), address="А", type="apartment",
            size_m2=50.0, purchase_price=Decimal("5000000"), status="active",
        )
        prop2 = PropertyEntity(
            id=uuid4(), account_id=uuid4(), address="Б", type="apartment",
            size_m2=50.0, purchase_price=Decimal("3000000"), status="active",
        )
        mock_property_repo.list_by_account.return_value = PaginatedResult(
            items=[prop1, prop2], total=2, page=1, per_page=20, pages=1,
        )
        mock_payment_repo.list_by_contract.return_value = []
        mock_contract_repo.get_active_for_property.return_value = None

        result = service.calculate_portfolio_roi(uuid4())
        assert result["properties_with_roi"] == 2
        assert result["portfolio_roi"] == 0.0