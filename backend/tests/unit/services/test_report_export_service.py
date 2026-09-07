"""Unit-тесты экспорта отчётов."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.domain.entities import (
    ContractEntity,
    PaymentEntity,
    PropertyEntity,
    PropertyExpenseEntity,
    RentChargeEntity,
    TenantEntity,
)
from app.services.report_export_service import ReportExportService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def repos(account_id):
    payment_repo = Mock()
    charge_repo = Mock()
    expense_repo = Mock()
    contract_repo = Mock()
    property_repo = Mock()
    tenant_repo = Mock()

    property_id = uuid4()
    tenant_id = uuid4()
    contract_id = uuid4()
    charge_id = uuid4()

    contract = ContractEntity(
        id=contract_id,
        account_id=account_id,
        property_id=property_id,
        tenant_id=tenant_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_amount=Decimal("50000"),
        currency="RUB",
        payment_day=5,
        status="active",
    )
    prop = PropertyEntity(
        id=property_id,
        account_id=account_id,
        city="Москва",
        street="Тверская",
        house="1",
        type="apartment",
        size_m2=50.0,
    )
    tenant = TenantEntity(
        id=tenant_id, account_id=account_id, full_name="Иван Иванов"
    )

    payment_repo.list_by_account.return_value = [
        PaymentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            date_paid=date(2026, 3, 5),
            amount=Decimal("50000"),
            currency="RUB",
            method="transfer",
            rent_charge_id=charge_id,
            note=None,
        )
    ]
    payment_repo.get_total_paid_for_charge.return_value = Decimal("50000")
    charge_repo.list_by_account.return_value = [
        RentChargeEntity(
            id=charge_id,
            account_id=account_id,
            contract_id=contract_id,
            due_date=date(2026, 3, 5),
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            amount=Decimal("50000"),
            currency="RUB",
            status="paid",
        ),
        RentChargeEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            due_date=date(2026, 1, 5),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            amount=Decimal("50000"),
            currency="RUB",
            status="paid",
        ),
    ]
    expense_repo.list_by_account.return_value = [
        PropertyExpenseEntity(
            id=uuid4(),
            account_id=account_id,
            property_id=property_id,
            category="utilities",
            amount=Decimal("3000"),
            currency="RUB",
            date_incurred=date(2026, 3, 10),
            note="ЖКХ март",
        )
    ]
    contract_repo.get_by_id.return_value = contract
    property_repo.get_by_id.return_value = prop
    tenant_repo.get_by_id.return_value = tenant

    return (
        payment_repo,
        charge_repo,
        expense_repo,
        contract_repo,
        property_repo,
        tenant_repo,
        contract_id,
    )


@pytest.fixture
def service(repos):
    payment_repo, charge_repo, expense_repo, contract_repo, property_repo, tenant_repo, _ = (
        repos
    )
    return ReportExportService(
        payment_repo,
        charge_repo,
        expense_repo,
        contract_repo,
        property_repo,
        tenant_repo,
    )


class TestReportExportService:
    def test_xlsx_export(self, service, account_id):
        content, media, filename = service.export(
            account_id, date(2026, 3, 1), date(2026, 3, 31), fmt="xlsx"
        )
        assert media.startswith("application/vnd.openxmlformats")
        assert filename.endswith(".xlsx")
        assert len(content) > 100

    def test_csv_export_includes_rows(self, service, account_id):
        content, media, filename = service.export(
            account_id, date(2026, 3, 1), date(2026, 3, 31), fmt="csv"
        )
        text = content.decode("utf-8-sig")
        assert "payment" in text
        assert "charge" in text
        assert "expense" in text
        assert "Итого платежи" in text
        assert filename.endswith(".csv")

    def test_empty_period(self, service, account_id, repos):
        payment_repo = repos[0]
        charge_repo = repos[1]
        expense_repo = repos[2]
        payment_repo.list_by_account.return_value = []
        charge_repo.list_by_account.return_value = []
        expense_repo.list_by_account.return_value = []
        content, _, _ = service.export(
            account_id, date(2026, 6, 1), date(2026, 6, 30), fmt="csv"
        )
        text = content.decode("utf-8-sig")
        assert "Итого платежи" in text
        assert "0" in text

    def test_invalid_dates(self, service, account_id):
        with pytest.raises(ValidationError):
            service.export(account_id, date(2026, 3, 31), date(2026, 3, 1), fmt="xlsx")
