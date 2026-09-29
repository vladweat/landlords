"""Каталог тарифов SaaS и лимиты."""

from dataclasses import dataclass
from enum import Enum


class PlanId(str, Enum):
    """Идентификатор тарифа."""

    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(str, Enum):
    """Статус SaaS-подписки аккаунта."""

    NONE = "none"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


DEFAULT_PLAN = PlanId.FREE.value
DEFAULT_SUBSCRIPTION_STATUS = SubscriptionStatus.NONE.value
DEFAULT_PRO_PRICE_RUB = 990

PLAN_LABELS_RU: dict[str, str] = {
    PlanId.FREE.value: "Free",
    PlanId.PRO.value: "Pro",
    PlanId.ENTERPRISE.value: "Enterprise",
}

# Тарифы, которые можно выставить вручную через PATCH /account/plan
MANUAL_CHANGE_PLANS = frozenset({PlanId.FREE.value, PlanId.ENTERPRISE.value})


@dataclass(frozen=True)
class PlanLimits:
    """Лимиты тарифа."""

    max_properties: int
    max_users: int
    max_storage_bytes: int


PLAN_LIMITS: dict[str, PlanLimits] = {
    PlanId.FREE.value: PlanLimits(
        max_properties=3,
        max_users=2,
        max_storage_bytes=100 * 1024 * 1024,
    ),
    PlanId.PRO.value: PlanLimits(
        max_properties=25,
        max_users=5,
        max_storage_bytes=5 * 1024 * 1024 * 1024,
    ),
    PlanId.ENTERPRISE.value: PlanLimits(
        max_properties=200,
        max_users=20,
        max_storage_bytes=50 * 1024 * 1024 * 1024,
    ),
}

# Цена в рублях в месяц; None = без оплаты через ЮKassa
PLAN_PRICE_RUB_MONTHLY: dict[str, int | None] = {
    PlanId.FREE.value: None,
    PlanId.PRO.value: DEFAULT_PRO_PRICE_RUB,
    PlanId.ENTERPRISE.value: None,
}


def is_valid_plan(plan: str) -> bool:
    """Проверить, что код тарифа известен."""
    return plan in PLAN_LIMITS


def get_plan_limits(plan: str) -> PlanLimits:
    """Лимиты тарифа; неизвестный код → Free."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[DEFAULT_PLAN])


def get_plan_price_rub(plan: str, *, pro_override: int | None = None) -> int | None:
    """Месячная цена тарифа в рублях."""
    if plan == PlanId.PRO.value and pro_override is not None:
        return pro_override
    return PLAN_PRICE_RUB_MONTHLY.get(plan)


def list_plans_catalog(*, pro_price_rub: int | None = None) -> list[dict]:
    """Каталог тарифов для API."""
    result: list[dict] = []
    for plan_id in (PlanId.FREE, PlanId.PRO, PlanId.ENTERPRISE):
        limits = PLAN_LIMITS[plan_id.value]
        result.append(
            {
                "id": plan_id.value,
                "name": PLAN_LABELS_RU[plan_id.value],
                "max_properties": limits.max_properties,
                "max_users": limits.max_users,
                "max_storage_bytes": limits.max_storage_bytes,
                "price_rub_monthly": get_plan_price_rub(
                    plan_id.value, pro_override=pro_price_rub
                ),
            }
        )
    return result
