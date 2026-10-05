"""Celery tasks for SaaS billing renewals."""

from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import OperationalError

from app.db.repositories.account_repo import AccountRepository
from app.db.session import SessionLocal
from app.services.billing_service import BillingService
from app.services.yookassa_client import YooKassaClient
from app.tasks.lock import RedisLock

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.billing_tasks.process_subscription_renewals",
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=300,
    time_limit=360,
    autoretry_for=(OperationalError,),
)
def process_subscription_renewals() -> dict[str, Any]:
    """Продлить Pro или отключить при неоплате (ежедневно)."""
    lock = RedisLock("process_subscription_renewals", ttl=600)
    if not lock.try_acquire():
        logger.info("process_subscription_renewals: lock not acquired")
        return {"status": "skipped", "reason": "lock_not_acquired"}

    session = SessionLocal()
    try:
        service = BillingService(AccountRepository(session), YooKassaClient())
        result = service.process_renewals(now=datetime.now(timezone.utc))
        session.commit()
        from app.services.ops_heartbeat import mark_beat_ok

        mark_beat_ok()
        logger.info("Subscription renewals done: %s", result)
        return {"status": "success", **result}
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
