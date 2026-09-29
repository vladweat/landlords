"""Unit-тесты PlanLimitService."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationError
from app.domain.entities import AccountEntity
from app.services.plan_limit_service import PlanLimitService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def account(account_id):
    return AccountEntity(
        id=account_id,
        name="Test",
        owner_id=uuid4(),
        plan="free",
    )


@pytest.fixture
def service(account):
    account_repo = Mock()
    property_repo = Mock()
    membership_repo = Mock()
    invite_repo = Mock()
    document_repo = Mock()
    account_repo.get_by_id.return_value = account
    property_repo.count_by_account.return_value = 0
    membership_repo.count_active_by_account.return_value = 1
    invite_repo.count_pending.return_value = 0
    document_repo.sum_size_bytes.return_value = 0
    return PlanLimitService(
        account_repo, property_repo, membership_repo, invite_repo, document_repo
    ), property_repo, membership_repo, invite_repo, document_repo


class TestPlanLimitService:
    def test_assert_can_create_property_ok(self, service, account_id):
        svc, *_ = service
        svc.assert_can_create_property(account_id)

    def test_assert_can_create_property_limit(self, service, account_id):
        svc, property_repo, *_ = service
        property_repo.count_by_account.return_value = 3
        with pytest.raises(ValidationError, match="максимум 3 объектов"):
            svc.assert_can_create_property(account_id)

    def test_assert_can_add_user_invite_counts_pending(self, service, account_id):
        svc, _, membership_repo, invite_repo, _ = service
        membership_repo.count_active_by_account.return_value = 1
        invite_repo.count_pending.return_value = 1
        with pytest.raises(ValidationError, match="максимум 2 пользователей"):
            svc.assert_can_add_user(account_id, for_invite=True)

    def test_assert_can_add_user_accept_only_active(self, service, account_id):
        svc, _, membership_repo, invite_repo, _ = service
        membership_repo.count_active_by_account.return_value = 1
        invite_repo.count_pending.return_value = 1
        svc.assert_can_add_user(account_id, for_invite=False)

    def test_assert_can_upload_limit(self, service, account_id):
        svc, *_, document_repo = service
        document_repo.sum_size_bytes.return_value = 100 * 1024 * 1024
        with pytest.raises(ValidationError, match="хранилище"):
            svc.assert_can_upload(account_id, 1)

    def test_change_plan_pro_in_development(self, service, account_id, account, monkeypatch):
        from app.core.config import settings

        monkeypatch.setattr(settings, "APP_ENV", "development")
        svc, *_ = service
        svc.account_repo.update.side_effect = lambda e: e
        dto = svc.change_plan(account_id, "pro")
        assert dto.plan == "pro"
        assert account.plan == "pro"

    def test_change_plan_pro_forbidden_outside_dev(
        self, service, account_id, monkeypatch
    ):
        from app.core.config import settings

        monkeypatch.setattr(settings, "APP_ENV", "production")
        svc, *_ = service
        with pytest.raises(ValidationError, match="оплату"):
            svc.change_plan(account_id, "pro")

    def test_change_plan_invalid(self, service, account_id):
        svc, *_ = service
        with pytest.raises(ValidationError, match="Неизвестный тариф"):
            svc.change_plan(account_id, "gold")

    def test_get_subscription(self, service, account_id):
        svc, *_ = service
        data = svc.get_subscription(account_id)
        assert data["plan"] == "free"
        assert data["limits"]["max_properties"] == 3
        assert len(data["plans_catalog"]) == 3
        assert "subscription_status" in data
        assert "billing_enabled" in data
        assert data["plans_catalog"][1]["price_rub_monthly"] == 990
