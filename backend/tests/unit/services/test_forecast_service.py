"""Unit tests for the account forecast query shape."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from app.domain.entities import ContractEntity, PropertyEntity, RentChargeEntity
from app.services.forecast_service import ForecastService


def _contract(property_id):
    today = date.today()
    return ContractEntity(
        id=uuid4(),
        account_id=uuid4(),
        property_id=property_id,
        tenant_id=uuid4(),
        start_date=today - timedelta(days=30),
        end_date=today + timedelta(days=20),
        rent_amount=Decimal("50000"),
        payment_day=5,
        status="active",
    )


def test_forecast_loads_charges_and_properties_in_batches():
    account_id = uuid4()
    properties = [
        PropertyEntity(
            id=uuid4(),
            account_id=account_id,
            city="Москва",
            street="Тестовая",
            house=str(i),
        )
        for i in (1, 2)
    ]
    contracts = [_contract(prop.id) for prop in properties]
    charges = [
        RentChargeEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract.id,
            due_date=date.today() + timedelta(days=3),
            period_start=date.today(),
            period_end=date.today() + timedelta(days=30),
            amount=Decimal("50000"),
        )
        for contract in contracts
    ]
    contract_repo = Mock()
    contract_repo.list_all_by_account.return_value = contracts
    charge_repo = Mock()
    charge_repo.list_by_contracts.return_value = charges
    property_repo = Mock()
    property_repo.list_by_ids.return_value = properties

    result = ForecastService(contract_repo, charge_repo, property_repo).get_forecast(
        account_id
    )

    assert result["total_to_year_end"] == "100000"
    charge_repo.list_by_contracts.assert_called_once_with(
        [contract.id for contract in contracts],
        account_id,
        date_from=date.today(),
        date_to=date(date.today().year, 12, 31),
    )
    property_repo.list_by_ids.assert_called_once_with(
        [contract.property_id for contract in contracts], account_id
    )
