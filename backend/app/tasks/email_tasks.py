"""Celery tasks for email notifications."""

from typing import Any

from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.email_dispatch_log_repo import EmailDispatchLogRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.services.calendar_service import CalendarService
from app.services.email_service import EmailService
from app.services.reminder_email_service import ReminderEmailService
from app.tasks.lock import RedisLock
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.email_tasks.send_daily_reminder_emails",
    retry_backoff=True,
    retry_kwargs={"max_retries": 2},
    soft_time_limit=300,
    time_limit=600,
)
def send_daily_reminder_emails() -> dict[str, Any]:
    """Ежедневная рассылка писем owner о просрочках и конце договоров."""
    lock = RedisLock("send_daily_reminder_emails", ttl=600)
    if not lock.try_acquire():
        logger.info("send_daily_reminder_emails: lock not acquired")
        return {"status": "skipped", "reason": "lock_not_acquired"}

    session = SessionLocal()
    try:
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
        )
        stats = service.send_daily_reminders()
        session.commit()
        logger.info("Daily reminder emails: {}", stats)
        return {"status": "success", **stats}
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
