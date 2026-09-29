"""Сервис тарифов и лимитов аккаунта."""

from uuid import UUID

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.billing import is_subscription_write_blocked
from app.domain.interfaces import (
    IAccountInviteRepository,
    IAccountRepository,
    IDocumentRepository,
    IMembershipRepository,
    IPropertyRepository,
)
from app.domain.plans import (
    MANUAL_CHANGE_PLANS,
    PLAN_LABELS_RU,
    PlanId,
    get_plan_limits,
    is_valid_plan,
    list_plans_catalog,
)
from app.services.dto.account_dto import AccountDTO


class PlanLimitService:
    """Usage, каталог тарифов и проверки лимитов."""

    def __init__(
        self,
        account_repo: IAccountRepository,
        property_repo: IPropertyRepository,
        membership_repo: IMembershipRepository,
        invite_repo: IAccountInviteRepository,
        document_repo: IDocumentRepository,
    ) -> None:
        self.account_repo = account_repo
        self.property_repo = property_repo
        self.membership_repo = membership_repo
        self.invite_repo = invite_repo
        self.document_repo = document_repo

    def get_usage(self, account_id: UUID) -> dict:
        """Текущее использование ресурсов аккаунта."""
        return {
            "properties": self.property_repo.count_by_account(account_id),
            "users": self.membership_repo.count_active_by_account(account_id),
            "storage_bytes": self.document_repo.sum_size_bytes(account_id),
        }

    def get_subscription(self, account_id: UUID) -> dict:
        """Тариф, лимиты, usage и каталог."""
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        limits = get_plan_limits(account.plan)
        return {
            "plan": account.plan,
            "plan_name": PLAN_LABELS_RU.get(account.plan, account.plan),
            "subscription_status": account.subscription_status,
            "subscription_period_end": account.subscription_period_end,
            "billing_enabled": settings.billing_enabled,
            "write_blocked": is_subscription_write_blocked(
                account, grace_days=settings.BILLING_GRACE_DAYS
            ),
            "limits": {
                "max_properties": limits.max_properties,
                "max_users": limits.max_users,
                "max_storage_bytes": limits.max_storage_bytes,
            },
            "usage": self.get_usage(account_id),
            "plans_catalog": list_plans_catalog(
                pro_price_rub=settings.BILLING_PRO_PRICE_RUB
            ),
        }

    def change_plan(self, account_id: UUID, plan: str) -> AccountDTO:
        """Сменить тариф вручную (free/enterprise; pro — только в development)."""
        if not is_valid_plan(plan):
            raise ValidationError(
                f"Неизвестный тариф: {plan}. Допустимы: free, pro, enterprise"
            )
        allowed = set(MANUAL_CHANGE_PLANS)
        if settings.APP_ENV == "development":
            allowed.add(PlanId.PRO.value)
        if plan not in allowed:
            if plan == PlanId.PRO.value:
                raise ValidationError(
                    "Тариф Pro оформляется через оплату. "
                    "Используйте кнопку «Оплатить Pro»."
                )
            raise ValidationError(f"Тариф {plan} нельзя выбрать вручную")

        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        account.plan = plan
        if plan == PlanId.FREE.value:
            account.subscription_status = "none"
            account.subscription_period_end = None
            account.yookassa_payment_method_id = None
        elif plan == PlanId.ENTERPRISE.value:
            account.subscription_status = "none"
            account.yookassa_payment_method_id = None
        updated = self.account_repo.update(account)
        return AccountDTO.model_validate(updated)

    def assert_can_create_property(self, account_id: UUID) -> None:
        """Проверить лимит объектов перед созданием."""
        account = self._require_account(account_id)
        limits = get_plan_limits(account.plan)
        current = self.property_repo.count_by_account(account_id)
        if current >= limits.max_properties:
            label = PLAN_LABELS_RU.get(account.plan, account.plan)
            raise ValidationError(
                f"Достигнут лимит тарифа {label}: максимум "
                f"{limits.max_properties} объектов"
            )

    def assert_can_add_user(self, account_id: UUID, *, for_invite: bool = True) -> None:
        """Проверить лимит пользователей (seats).

        for_invite=True: учитывает active + pending invites (слот под новый инвайт).
        for_invite=False: только active (при accept).
        """
        account = self._require_account(account_id)
        limits = get_plan_limits(account.plan)
        active = self.membership_repo.count_active_by_account(account_id)
        if for_invite:
            pending = self.invite_repo.count_pending(account_id)
            occupied = active + pending
        else:
            occupied = active
        if occupied >= limits.max_users:
            label = PLAN_LABELS_RU.get(account.plan, account.plan)
            raise ValidationError(
                f"Достигнут лимит тарифа {label}: максимум "
                f"{limits.max_users} пользователей"
            )

    def assert_can_upload(self, account_id: UUID, extra_bytes: int) -> None:
        """Проверить лимит хранилища перед записью файла."""
        if extra_bytes < 0:
            raise ValidationError("Некорректный размер файла")
        account = self._require_account(account_id)
        limits = get_plan_limits(account.plan)
        used = self.document_repo.sum_size_bytes(account_id)
        if used + extra_bytes > limits.max_storage_bytes:
            label = PLAN_LABELS_RU.get(account.plan, account.plan)
            raise ValidationError(
                f"Достигнут лимит тарифа {label}: недостаточно места "
                f"в хранилище"
            )

    def _require_account(self, account_id: UUID):
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Account not found")
        return account
