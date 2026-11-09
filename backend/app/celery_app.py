"""Celery-приложение."""

from celery import Celery
from celery.schedules import crontab
from celery.signals import task_failure, task_postrun, task_prerun

from app.core.config import settings
from app.services.ops_task_metrics import record_task_event


def _init_sentry() -> None:
    """Initialize Sentry for Celery workers if DSN is provided."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            release=settings.APP_VERSION,
            integrations=[CeleryIntegration(), SqlalchemyIntegration()],
            traces_sample_rate=0.1 if settings.APP_ENV == "production" else 0.0,
        )
    except Exception:
        # don't fail worker startup if Sentry initialization fails
        pass


_init_sentry()

celery_app = Celery("app")

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    broker_transport_options={"global_keyprefix": settings.REDIS_KEY_PREFIX},
    result_backend_transport_options={"global_keyprefix": settings.REDIS_KEY_PREFIX},
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=(
        "app.tasks.charge_tasks",
        "app.tasks.email_tasks",
        "app.tasks.billing_tasks",
        "app.tasks.ops_tasks",
        "app.tasks.payment_idempotency_tasks",
    ),
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "update-overdue-charges-daily": {
            "task": "app.tasks.charge_tasks.update_overdue_charges",
            "schedule": crontab(hour=3, minute=0),
        },
        "send-daily-reminder-emails": {
            "task": "app.tasks.email_tasks.send_daily_reminder_emails",
            "schedule": crontab(hour=7, minute=0),
        },
        "process-subscription-renewals-daily": {
            "task": "app.tasks.billing_tasks.process_subscription_renewals",
            "schedule": crontab(hour=4, minute=0),
        },
        "check-ops-health-hourly": {
            "task": "app.tasks.ops_tasks.check_ops_health",
            "schedule": crontab(minute=15),
        },
        "cleanup-expired-payment-idempotency-records-hourly": {
            "task": (
                "app.tasks.payment_idempotency_tasks."
                "cleanup_expired_payment_idempotency_records"
            ),
            "schedule": crontab(minute=45),
        },
    },
)

def _task_name(task, sender) -> str:
    """Return only the registered task name; never inspect task arguments."""
    return getattr(task, "name", None) or getattr(sender, "name", str(sender))


@task_prerun.connect
def _on_task_prerun(sender=None, task=None, **_):
    """Record task start without capturing its ID or input payload."""
    record_task_event(_task_name(task, sender), "started")


@task_postrun.connect
def _on_task_postrun(sender=None, task=None, retval=None, state=None, **_):
    """Record successful or explicitly skipped task outcomes once."""
    if state != "SUCCESS":
        return
    status = "skipped" if isinstance(retval, dict) and retval.get("status") == "skipped" else "success"
    record_task_event(_task_name(task, sender), status)


@task_failure.connect
def _on_task_failure(sender=None, **_):
    """Record terminal task failure; task_postrun ignores the FAILURE state."""
    record_task_event(_task_name(sender, sender), "failure")
