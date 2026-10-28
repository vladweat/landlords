"""Celery tasks for email notifications."""

import smtplib
import socket
from typing import Any

from sqlalchemy.exc import OperationalError

from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.email_dispatch_log_repo import EmailDispatchLogRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_context_repo import TenantContextRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.db.tenant_context import set_tenant_context
from app.services.calendar_service import CalendarService
from app.services.email_service import EmailService
from app.services.reminder_email_service import ReminderEmailService
from app.tasks.lock import RedisLock, SCHEDULED_TASK_LOCK_TTL_SECONDS
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


class TransientEmailDeliveryError(Exception):
    """Временная ошибка SMTP, для которой допустим ограниченный повтор."""


@shared_task(
    name="app.tasks.email_tasks.send_daily_reminder_emails",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 2},
    autoretry_for=(
        OperationalError,
        smtplib.SMTPServerDisconnected,
        socket.timeout,
        ConnectionError,
        TransientEmailDeliveryError,
    ),
    soft_time_limit=300,
    time_limit=600,
)
def send_daily_reminder_emails() -> dict[str, Any]:
    """Ежедневная рассылка писем owner о просрочках и конце договоров."""
    lock = RedisLock(
        "send_daily_reminder_emails", ttl=SCHEDULED_TASK_LOCK_TTL_SECONDS
    )
    if not lock.try_acquire():
        logger.info("send_daily_reminder_emails: lock not acquired")
        return {"status": "skipped", "reason": "lock_not_acquired"}

    session = SessionLocal()
    try:
        context_repo = TenantContextRepository(session)
        service = ReminderEmailService(
            account_repo=AccountRepository(session),
            user_repo=UserRepository(session),
            calendar_service=CalendarService(
                RentChargeRepository(session),
                PaymentRepository(session),
                ContractRepository(session),
                PropertyRepository(session),
                TenantRepository(session),
            ),
            dispatch_log_repo=EmailDispatchLogRepository(session),
            email_service=EmailService(),
            commit=lambda: _commit_with_tenant_context(session, account_id),
        )
        aggregate = {"sent": 0, "skipped": 0, "errors": 0, "retryable_errors": 0}
        for account_id in context_repo.account_ids():
            set_tenant_context(session, account_id)
            stats = service.send_daily_reminders(account_id)
            for key in aggregate:
                aggregate[key] += stats.get(key, 0)
            session.commit()

        if aggregate.get("retryable_errors", 0):
            raise TransientEmailDeliveryError(
                f"SMTP temporarily failed for {aggregate['retryable_errors']} reminder(s)"
            )
        from app.services.ops_heartbeat import mark_beat_ok

        mark_beat_ok()
        logger.info("Daily reminder emails: {}", aggregate)
        return {"status": "success", **aggregate}
    except Exception:
        session.rollback()
        logger.exception("Failed send_daily_reminder_emails")
        raise
    finally:
        try:
            lock.release()
        except Exception:
            pass
        session.close()


def _commit_with_tenant_context(session, account_id) -> None:
    """Зафиксировать dedup row и восстановить tenant scope новой транзакции."""
    session.commit()
    set_tenant_context(session, account_id)
