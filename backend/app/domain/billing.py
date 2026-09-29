"""Правила SaaS-биллинга (подписка, write-block)."""

from datetime import datetime, timedelta, timezone

from app.domain.entities import AccountEntity
from app.domain.plans import PlanId, SubscriptionStatus


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_subscription_write_blocked(
    account: AccountEntity,
    *,
    grace_days: int,
    now: datetime | None = None,
) -> bool:
    """Read-only после grace при past_due; Free/Enterprise без past_due не блокируются."""
    if account.subscription_status != SubscriptionStatus.PAST_DUE.value:
        return False
    moment = now or datetime.now(timezone.utc)
    if account.subscription_period_end is None:
        return True
    grace_end = _as_utc(account.subscription_period_end) + timedelta(days=grace_days)
    return moment > grace_end


def is_pro_period_due(
    account: AccountEntity,
    *,
    now: datetime | None = None,
) -> bool:
    """Pro с истёкшим периодом — кандидат на автоплатёж или отключение."""
    if account.plan != PlanId.PRO.value:
        return False
    if account.subscription_period_end is None:
        return True
    moment = now or datetime.now(timezone.utc)
    return _as_utc(account.subscription_period_end) <= moment
