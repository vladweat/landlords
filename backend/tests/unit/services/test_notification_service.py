"""Unit-тесты сервиса UI-уведомлений."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.services.dto.calendar_dto import CalendarEventDTO
from app.services.notification_service import NotificationService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def contract_id():
    return uuid4()


@pytest.fixture
def charge_id():
    return uuid4()


@pytest.fixture
def calendar_service():
    return Mock()


@pytest.fixture
def dismissal_repo():
    repo = Mock()
    repo.list_keys.return_value = set()
    return repo


@pytest.fixture
def service(calendar_service, dismissal_repo):
    return NotificationService(calendar_service, dismissal_repo)


class TestNotificationService:
    def test_overdue_and_ending(
        self, service, calendar_service, account_id, user_id, contract_id, charge_id
    ):
        """Просрочка и окончание договора попадают в inbox."""
        today = date.today()
        calendar_service.get_events.return_value = [
            CalendarEventDTO(
                type="charge_due",
                date=today - timedelta(days=5),
                contract_id=contract_id,
                property_address="Москва, Тверская, 1",
                tenant_name="Иван",
                charge_id=charge_id,
                amount=Decimal("50000"),
                amount_paid=Decimal("0"),
                remaining=Decimal("50000"),
                status="overdue",
                currency="RUB",
            ),
            CalendarEventDTO(
                type="charge_due",
                date=today + timedelta(days=3),
                contract_id=contract_id,
                charge_id=uuid4(),
                amount=Decimal("50000"),
                amount_paid=Decimal("0"),
                remaining=Decimal("50000"),
                status="pending",
                currency="RUB",
            ),
            CalendarEventDTO(
                type="contract_ending",
                date=today + timedelta(days=20),
                contract_id=contract_id,
                property_address="Москва, Тверская, 1",
                tenant_name="Иван",
                rent_amount=Decimal("50000"),
                days_until_end=20,
                currency="RUB",
            ),
        ]

        result = service.list_notifications(account_id, user_id)

        assert result.unread_count == 2
        types = {i.type for i in result.items}
        assert types == {"charge_overdue", "contract_ending"}
        overdue = next(i for i in result.items if i.type == "charge_overdue")
        assert overdue.id == f"overdue:{charge_id}"
        assert overdue.severity == "critical"

    def test_dismiss_hides_item(
        self,
        service,
        calendar_service,
        dismissal_repo,
        account_id,
        user_id,
        contract_id,
        charge_id,
    ):
        """Dismiss скрывает ключ из списка."""
        today = date.today()
        key = f"overdue:{charge_id}"
        dismissal_repo.list_keys.return_value = {key}
        calendar_service.get_events.return_value = [
            CalendarEventDTO(
                type="charge_due",
                date=today - timedelta(days=2),
                contract_id=contract_id,
                charge_id=charge_id,
                amount=Decimal("10000"),
                amount_paid=Decimal("0"),
                remaining=Decimal("10000"),
                status="overdue",
                currency="RUB",
            ),
        ]

        result = service.list_notifications(account_id, user_id)
        assert result.unread_count == 0
        assert result.items == []

    def test_dismiss_calls_repo(self, service, dismissal_repo, account_id, user_id):
        """dismiss сохраняет ключ."""
        service.dismiss(account_id, user_id, "ending:abc")
        dismissal_repo.dismiss.assert_called_once()
        entity = dismissal_repo.dismiss.call_args[0][0]
        assert entity.notification_key == "ending:abc"
        assert entity.account_id == account_id
        assert entity.user_id == user_id
