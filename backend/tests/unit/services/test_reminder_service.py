"""Unit-тесты сервиса напоминаний."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractEntity, RentChargeEntity, TenantEntity
from app.services.dto.reminder_dto import ReminderCreateDTO
from app.services.reminder_service import ReminderService
from app.domain.entities import ReminderEntity


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def mock_reminder_repo():
    repo = Mock()
    repo.count_by_charge.return_value = 0
    repo.get_by_charge.return_value = []
    repo.create.return_value = ReminderEntity(
        id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
        charge_id=uuid4(), reminder_type="first",
        message_text="Иван, добрый день! Напоминаю...",
        created_at=_utc_now(),
    )
    return repo

@pytest.fixture
def mock_charge_repo():
    repo = Mock()
    repo.get_by_id.return_value = RentChargeEntity(
        id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
        due_date=date.today() - timedelta(days=5),
        period_start=date.today() - timedelta(days=35),
        period_end=date.today() - timedelta(days=5),
        amount=Decimal("50000"), currency="RUB", status="overdue",
    )
    return repo


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.get_by_id.return_value = ContractEntity(
        id=uuid4(), account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
        start_date=date.today() - timedelta(days=365),
        end_date=date.today() + timedelta(days=365),
        rent_amount=Decimal("50000"), currency="RUB", payment_day=5, status="active",
    )
    return repo


@pytest.fixture
def mock_tenant_repo():
    repo = Mock()
    repo.get_by_id.return_value = TenantEntity(
        id=uuid4(), account_id=uuid4(), full_name="Иван Петров",
    )
    return repo


@pytest.fixture
def service(mock_reminder_repo, mock_charge_repo, mock_contract_repo, mock_tenant_repo):
    return ReminderService(mock_reminder_repo, mock_charge_repo, mock_contract_repo, mock_tenant_repo)


class TestGenerateMessage:
    def test_first_reminder(self, service):
        charge_id = uuid4()
        msg = service.generate_message(charge_id, uuid4(), "first")
        assert "добрый день" in msg.lower()
        assert "50000" in msg

    def test_second_reminder(self, service):
        charge_id = uuid4()
        msg = service.generate_message(charge_id, uuid4(), "second")
        assert "до сих пор не поступила" in msg.lower()

    def test_third_reminder(self, service):
        charge_id = uuid4()
        msg = service.generate_message(charge_id, uuid4(), "third")
        assert "третье уведомление" in msg.lower()

    def test_includes_invoice_url_when_present(
        self, mock_reminder_repo, mock_charge_repo, mock_contract_repo, mock_tenant_repo
    ):
        from app.domain.entities import InvoiceEntity

        invoice_repo = Mock()
        invoice_repo.get_by_charge.return_value = InvoiceEntity(
            id=uuid4(),
            account_id=uuid4(),
            contract_id=uuid4(),
            charge_id=uuid4(),
            public_token="abcTOKEN",
        )
        service = ReminderService(
            mock_reminder_repo,
            mock_charge_repo,
            mock_contract_repo,
            mock_tenant_repo,
            invoice_repo=invoice_repo,
        )
        msg = service.generate_message(uuid4(), uuid4(), "first")
        assert "Квитанция:" in msg
        assert "/i/abcTOKEN" in msg


class TestCreateReminder:
    def test_success(self, service, mock_reminder_repo):
        dto = ReminderCreateDTO(charge_id=uuid4(), reminder_type="first")
        result = service.create_reminder(uuid4(), dto)
        assert result.reminder_type == "first"
        assert "Иван" in result.message_text

    def test_creates_russian_contract_event(
        self, mock_reminder_repo, mock_charge_repo, mock_contract_repo, mock_tenant_repo
    ):
        event_repo = Mock()
        service = ReminderService(
            mock_reminder_repo,
            mock_charge_repo,
            mock_contract_repo,
            mock_tenant_repo,
            event_repo=event_repo,
        )
        dto = ReminderCreateDTO(charge_id=uuid4(), reminder_type="first")
        service.create_reminder(uuid4(), dto)
        event = event_repo.create.call_args[0][0]
        assert event.event_type == "reminder"
        assert event.title == "Напоминание о просрочке (первое)"
        assert "Иван" in event.description

    def test_charge_not_overdue(self, service, mock_charge_repo):
        mock_charge_repo.get_by_id.return_value.status = "paid"
        dto = ReminderCreateDTO(charge_id=uuid4(), reminder_type="first")
        with pytest.raises(ValidationError, match="overdue"):
            service.create_reminder(uuid4(), dto)

    def test_max_reminders_rejected(self, service, mock_reminder_repo):
        mock_reminder_repo.count_by_charge.return_value = 3
        dto = ReminderCreateDTO(charge_id=uuid4(), reminder_type="third")
        with pytest.raises(ValidationError, match="Maximum 3"):
            service.create_reminder(uuid4(), dto)


class TestShouldShowReminder:
    def test_first_reminder(self, service, mock_reminder_repo):
        mock_reminder_repo.count_by_charge.return_value = 0
        result = service.should_show_reminder(uuid4(), uuid4())
        assert result["can_remind"] is True
        assert result["reminder_type"] == "first"

    def test_cannot_remind_if_not_overdue(self, service, mock_charge_repo):
        mock_charge_repo.get_by_id.return_value.status = "paid"
        result = service.should_show_reminder(uuid4(), uuid4())
        assert result["can_remind"] is False