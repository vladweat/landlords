"""Unit-тесты сервиса календаря платежей."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import ContractEntity, PropertyEntity, RentChargeEntity, TenantEntity
from app.services.calendar_service import CalendarService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def property_id():
    return uuid4()


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def contract_id():
    return uuid4()


@pytest.fixture
def contract(account_id, property_id, tenant_id, contract_id):
    today = date.today()
    return ContractEntity(
        id=contract_id,
        account_id=account_id,
        property_id=property_id,
        tenant_id=tenant_id,
        start_date=today - timedelta(days=180),
        end_date=today + timedelta(days=20),
        rent_amount=Decimal("50000.00"),
        currency="RUB",
        payment_day=5,
        status="active",
    )


@pytest.fixture
def mock_repos(account_id, property_id, tenant_id, contract):
    charge_repo = Mock()
    payment_repo = Mock()
    contract_repo = Mock()
    property_repo = Mock()
    tenant_repo = Mock()

    charge_repo.list_for_calendar.return_value = []
    payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
    contract_repo.list_all_by_account.return_value = [contract]
    contract_repo.get_by_id.return_value = contract
    property_repo.get_by_id.return_value = PropertyEntity(
        id=property_id,
        account_id=account_id,
        city="Москва",
        street="Тверская",
        house="1",
        type="apartment",
        size_m2=50.0,
    )
    tenant_repo.get_by_id.return_value = TenantEntity(
        id=tenant_id,
        account_id=account_id,
        full_name="Иван Иванов",
    )
    return charge_repo, payment_repo, contract_repo, property_repo, tenant_repo


@pytest.fixture
def service(mock_repos):
    charge_repo, payment_repo, contract_repo, property_repo, tenant_repo = mock_repos
    return CalendarService(
        charge_repo, payment_repo, contract_repo, property_repo, tenant_repo
    )


class TestCalendarService:
    def test_contract_ending_in_window(self, service, mock_repos, contract):
        """Окончание договора в окне попадает в события."""
        events = service.get_events(contract.account_id)
        endings = [e for e in events if e.type == "contract_ending"]
        assert len(endings) == 1
        assert endings[0].contract_id == contract.id
        assert endings[0].rent_amount == Decimal("50000.00")
        assert endings[0].tenant_name == "Иван Иванов"
        assert "Тверская" in endings[0].property_address

    def test_overdue_charge_included(self, service, mock_repos, contract, account_id):
        """Просроченное начисление всегда в списке."""
        charge_repo, payment_repo, *_ = mock_repos
        charge_id = uuid4()
        charge_repo.list_for_calendar.return_value = [
            RentChargeEntity(
                id=charge_id,
                account_id=account_id,
                contract_id=contract.id,
                due_date=date.today() - timedelta(days=10),
                period_start=date.today() - timedelta(days=40),
                period_end=date.today() - timedelta(days=10),
                amount=Decimal("50000.00"),
                currency="RUB",
                status="pending",
            )
        ]
        payment_repo.get_total_paid_for_charge.return_value = Decimal("0")

        events = service.get_events(account_id)
        dues = [e for e in events if e.type == "charge_due"]
        assert len(dues) == 1
        assert dues[0].status == "overdue"
        assert dues[0].remaining == Decimal("50000.00")
        assert isinstance(dues[0].remaining, Decimal)
        # overdue first
        assert events[0].type == "charge_due"
        assert events[0].status == "overdue"

    def test_paid_charge_excluded(self, service, mock_repos, contract, account_id):
        """Полностью оплаченное начисление не попадает в календарь."""
        charge_repo, payment_repo, *_ = mock_repos
        charge_repo.list_for_calendar.return_value = [
            RentChargeEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract.id,
                due_date=date.today() + timedelta(days=5),
                period_start=date.today(),
                period_end=date.today() + timedelta(days=30),
                amount=Decimal("50000.00"),
                currency="RUB",
                status="pending",
            )
        ]
        payment_repo.get_total_paid_for_charge.return_value = Decimal("50000.00")

        events = service.get_events(account_id)
        assert all(e.type != "charge_due" for e in events)

    def test_upcoming_outside_window_excluded(
        self, service, mock_repos, contract, account_id
    ):
        """Будущее начисление за пределами to не включается."""
        charge_repo, payment_repo, *_ = mock_repos
        charge_repo.list_for_calendar.return_value = [
            RentChargeEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract.id,
                due_date=date.today() + timedelta(days=5),
                period_start=date.today(),
                period_end=date.today() + timedelta(days=30),
                amount=Decimal("50000.00"),
                currency="RUB",
                status="pending",
            )
        ]
        payment_repo.get_total_paid_for_charge.return_value = Decimal("0")

        today = date.today()
        events = service.get_events(
            account_id, date_from=today, date_to=today + timedelta(days=2)
        )
        assert all(e.type != "charge_due" for e in events)

    def test_draft_contract_ending_excluded(self, service, mock_repos, contract):
        """Draft-договор не даёт событие окончания."""
        _, _, contract_repo, *_ = mock_repos
        contract.status = "draft"
        contract_repo.list_all_by_account.return_value = [contract]
        events = service.get_events(contract.account_id)
        assert all(e.type != "contract_ending" for e in events)
