"""Unit tests for batched dashboard aggregation."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from app.domain.entities import (
    ContractEntity,
    PaymentEntity,
    PropertyEntity,
    TenantEntity,
)
from app.domain.pagination import PaginatedResult
from app.services.dashboard_service import DashboardService


def test_summary_batches_contract_tenant_payment_and_expense_reads():
    account_id = uuid4()
    today = date.today()
    properties = [
        PropertyEntity(
            id=uuid4(),
            account_id=account_id,
            city="Москва",
            street="Тестовая",
            house=str(i),
            purchase_price=Decimal("5000000"),
        )
        for i in (1, 2)
    ]
    tenants = [
        TenantEntity(id=uuid4(), account_id=account_id, full_name=f"Tenant {i}")
        for i in (1, 2)
    ]
    contracts = [
        ContractEntity(
            id=uuid4(),
            account_id=account_id,
            property_id=prop.id,
            tenant_id=tenant.id,
            start_date=today - timedelta(days=30),
            end_date=today + timedelta(days=20),
            rent_amount=Decimal("50000"),
            payment_day=5,
            status="active",
        )
        for prop, tenant in zip(properties, tenants, strict=True)
    ]
    payments = [
        PaymentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract.id,
            date_paid=today - timedelta(days=5),
            amount=Decimal("40000"),
        )
        for contract in contracts
    ]
    property_repo = Mock()
    property_repo.count_active.return_value = len(properties)
    property_repo.list_by_account.return_value = PaginatedResult(
        items=properties,
        total=2,
        page=1,
        per_page=1000,
        pages=1,
    )
    contract_repo = Mock()
    contract_repo.count_active.return_value = len(contracts)
    contract_repo.list_active_by_properties.return_value = contracts
    tenant_repo = Mock()
    tenant_repo.list_by_ids.return_value = tenants
    payment_repo = Mock()
    payment_repo.get_total_paid_for_month.return_value = Decimal("40000")
    payment_repo.get_monthly_income.return_value = Decimal("35000")
    payment_repo.list_by_contracts.return_value = payments
    charge_repo = Mock()
    charge_repo.get_total_expected_for_month.return_value = Decimal("50000")
    charge_repo.get_total_outstanding.return_value = Decimal("10000")
    charge_repo.get_overdue_total_amount.return_value = Decimal("0")
    charge_repo.get_overdue_count.return_value = 0
    expense_repo = Mock()
    expense_repo.sum_by_property_ids.return_value = {
        properties[0].id: Decimal("5000"),
        properties[1].id: Decimal("5000"),
    }

    result = DashboardService(
        property_repo,
        contract_repo,
        charge_repo,
        payment_repo,
        tenant_repo,
        expense_repo,
    ).get_summary(account_id)

    assert [item["tenant_name"] for item in result.properties_overview] == [
        "Tenant 1",
        "Tenant 2",
    ]
    assert [item["annual_income"] for item in result.properties_overview] == [
        "40000",
        "40000",
    ]
    assert [item["annual_expenses"] for item in result.properties_overview] == [
        "5000",
        "5000",
    ]
    contract_repo.list_active_by_properties.assert_called_once_with(
        [prop.id for prop in properties],
        account_id,
    )
    tenant_repo.list_by_ids.assert_called_once_with(
        [tenant.id for tenant in tenants], account_id
    )
    payment_repo.list_by_contracts.assert_called_once()
    expense_repo.sum_by_property_ids.assert_called_once()


def test_last_payments_batches_contract_property_and_tenant_reads():
    account_id = uuid4()
    prop = PropertyEntity(
        id=uuid4(), account_id=account_id, city="Москва", street="Тестовая", house="1"
    )
    tenant = TenantEntity(id=uuid4(), account_id=account_id, full_name="Tenant")
    contract = ContractEntity(
        id=uuid4(),
        account_id=account_id,
        property_id=prop.id,
        tenant_id=tenant.id,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        rent_amount=Decimal("50000"),
        payment_day=5,
        status="active",
    )
    payment = PaymentEntity(
        id=uuid4(),
        account_id=account_id,
        contract_id=contract.id,
        date_paid=date.today(),
        amount=Decimal("1000"),
    )
    payment_repo = Mock()
    payment_repo.list_by_account.return_value = [payment]
    contract_repo = Mock()
    contract_repo.list_all_by_account.return_value = [contract]
    property_repo = Mock()
    property_repo.list_by_ids.return_value = [prop]
    tenant_repo = Mock()
    tenant_repo.list_by_ids.return_value = [tenant]

    result = DashboardService(
        property_repo,
        contract_repo,
        Mock(),
        payment_repo,
        tenant_repo,
    ).get_last_payments(account_id)

    assert result[0]["tenant_name"] == "Tenant"
    assert result[0]["property_address"] == prop.get_address()
    contract_repo.list_all_by_account.assert_called_once_with(account_id)
    property_repo.list_by_ids.assert_called_once_with([prop.id], account_id)
    tenant_repo.list_by_ids.assert_called_once_with([tenant.id], account_id)
