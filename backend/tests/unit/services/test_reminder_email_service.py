"""Unit-тесты ReminderEmailService."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import AccountEntity, UserEntity
from app.services.dto.calendar_dto import CalendarEventDTO
from app.services.reminder_email_service import ReminderEmailService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def owner_id():
    return uuid4()


@pytest.fixture
def account(account_id, owner_id):
    return AccountEntity(id=account_id, name="Acc", owner_id=owner_id)


@pytest.fixture
def owner(owner_id):
    return UserEntity(
        id=owner_id,
        email="owner@example.com",
        password_hash="x",
        full_name="Owner",
    )


@pytest.fixture
def service(account, owner):
    account_repo = Mock()
    account_repo.list_all.return_value = [account]
    user_repo = Mock()
    user_repo.get_by_id.return_value = owner
    calendar = Mock()
    dispatch = Mock()
    dispatch.was_sent_recently.return_value = False
    email = Mock()
    return ReminderEmailService(account_repo, user_repo, calendar, dispatch, email), {
        "account_repo": account_repo,
        "user_repo": user_repo,
        "calendar": calendar,
        "dispatch": dispatch,
        "email": email,
        "account": account,
        "owner": owner,
    }


class TestReminderEmailService:
    def test_sends_overdue_to_owner(self, service, account_id):
        svc, mocks = service
        charge_id = uuid4()
        contract_id = uuid4()
        mocks["calendar"].get_events.return_value = [
            CalendarEventDTO(
                type="charge_due",
                date=date.today(),
                contract_id=contract_id,
                charge_id=charge_id,
                status="overdue",
                remaining=Decimal("1000"),
                currency="RUB",
                property_address="ул. Тест, 1",
                tenant_name="Иван",
            )
        ]

        stats = svc.send_daily_reminders()

        assert stats["sent"] == 1
        mocks["email"].send_charge_overdue.assert_called_once()
        mocks["dispatch"].record.assert_called_once()
        call_kw = mocks["email"].send_charge_overdue.call_args.kwargs
        assert call_kw["to"] == "owner@example.com"
        assert call_kw["remaining"] == "1000"

    def test_skips_dedup(self, service):
        svc, mocks = service
        mocks["dispatch"].was_sent_recently.return_value = True
        mocks["calendar"].get_events.return_value = [
            CalendarEventDTO(
                type="contract_ending",
                date=date.today(),
                contract_id=uuid4(),
                days_until_end=10,
                property_address="ул. Тест",
            )
        ]

        stats = svc.send_daily_reminders()

        assert stats["sent"] == 0
        assert stats["skipped"] == 1
        mocks["email"].send_contract_ending.assert_not_called()

    def test_sends_contract_ending(self, service):
        svc, mocks = service
        mocks["calendar"].get_events.return_value = [
            CalendarEventDTO(
                type="contract_ending",
                date=date.today(),
                contract_id=uuid4(),
                days_until_end=5,
                property_address="Дом 2",
            )
        ]

        stats = svc.send_daily_reminders()

        assert stats["sent"] == 1
        mocks["email"].send_contract_ending.assert_called_once()
