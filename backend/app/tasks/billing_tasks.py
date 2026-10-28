"""Celery tasks for SaaS billing renewals."""

from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import OperationalError

from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.tenant_context_repo import TenantContextRepository
from app.db.session import SessionLocal
from app.db.tenant_context import set_tenant_context
from app.services.billing_service import BillingService
from app.services.yookassa_client import YooKassaClient
from app.tasks.lock import RedisLock, SCHEDULED_TASK_LOCK_TTL_SECONDS

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.billing_tasks.process_subscription_renewals",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=300,
    time_limit=360,
    autoretry_for=(OperationalError,),
)
def process_subscription_renewals() -> dict[str, Any]:
    """Продлить Pro или отключить при неоплате (ежедневно)."""
    lock = RedisLock(
        "process_subscription_renewals", ttl=SCHEDULED_TASK_LOCK_TTL_SECONDS
    )
    if not lock.try_acquire():
        logger.info("process_subscription_renewals: lock not acquired")
        return {"status": "skipped", "reason": "lock_not_acquired"}

    session = SessionLocal()
    try:
        context_repo = TenantContextRepository(session)
        aggregate = {"renewed": 0, "past_due": 0, "downgraded": 0, "skipped": 0}
        for account_id in context_repo.account_ids():
            set_tenant_context(session, account_id)
            service = BillingService(
                AccountRepository(session),
                YooKassaClient(),
                commit=lambda: _commit_with_tenant_context(session, account_id),
                session=session,
            )
            result = service.process_renewals(
                now=datetime.now(timezone.utc), account_id=account_id
            )
            for key in aggregate:
                aggregate[key] += result.get(key, 0)
            session.commit()
        from app.services.ops_heartbeat import mark_beat_ok

        mark_beat_ok()
        logger.info("Subscription renewals done: %s", aggregate)
        return {"status": "success", **aggregate}
    except Exception:
        session.rollback()
        logger.exception("Subscription renewals failed")
        raise
    finally:
        try:
            lock.release()
        except Exception:
            pass
        session.close()


def _commit_with_tenant_context(session, account_id) -> None:
    """Зафиксировать renewal state до HTTP-вызова и восстановить tenant scope."""
    session.commit()
    set_tenant_context(session, account_id)
