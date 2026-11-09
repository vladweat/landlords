"""Cleanup tasks for expired payment request-idempotency records."""

from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import OperationalError

from app.db.repositories.payment_idempotency_repo import PaymentIdempotencyRepository
from app.db.repositories.tenant_context_repo import TenantContextRepository
from app.db.session import SessionLocal
from app.db.tenant_context import set_tenant_context
from app.services.payment_idempotency_service import PAYMENT_CREATE_SCOPE

logger = get_task_logger(__name__)
EXPIRED_RECORD_BATCH_SIZE = 500


@shared_task(
    name="app.tasks.payment_idempotency_tasks.cleanup_expired_payment_idempotency_records",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=300,
    time_limit=360,
    autoretry_for=(OperationalError,),
)
def cleanup_expired_payment_idempotency_records() -> dict[str, Any]:
    """Purge a bounded batch of expired response snapshots for each account."""
    session = SessionLocal()
    try:
        account_ids = TenantContextRepository(session).account_ids()
        repository = PaymentIdempotencyRepository(session)
        now = datetime.now(timezone.utc)
        records_deleted = 0
        for account_id in account_ids:
            set_tenant_context(session, account_id)
            records_deleted += repository.delete_expired_for_account(
                account_id=account_id,
                operation_scope=PAYMENT_CREATE_SCOPE,
                now=now,
                limit=EXPIRED_RECORD_BATCH_SIZE,
            )
            # Commit per tenant so a large account set does not hold one long
            # transaction. RLS context resets with each commit.
            session.commit()

        result = {
            "status": "success",
            "accounts_scanned": len(account_ids),
            "records_deleted": records_deleted,
        }
        logger.info(
            "payment_idempotency_cleanup accounts_scanned=%d records_deleted=%d",
            result["accounts_scanned"],
            result["records_deleted"],
        )
        return result
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
