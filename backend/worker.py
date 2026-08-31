"""Точка входа Celery-воркера."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("app")

celery_app.conf.update(
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    task_default_queue=settings.CELERY_TASK_DEFAULT_QUEUE,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("app.tasks.charge_tasks",),
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "update-overdue-charges-daily": {
            "task": "app.tasks.charge_tasks.update_overdue_charges",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)