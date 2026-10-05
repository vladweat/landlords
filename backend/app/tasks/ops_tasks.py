"""Celery: проверка свободного места под документы."""

from __future__ import annotations

from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger

from app.services.ops_alert_service import check_and_alert_disk, update_ops_gauges
from app.services.ops_heartbeat import mark_beat_ok

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.ops_tasks.check_ops_health",
    soft_time_limit=60,
    time_limit=90,
)
def check_ops_health() -> dict[str, Any]:
    """Часовая проверка диска; heartbeat подтверждает, что beat жив."""
    mark_beat_ok()
    snap = update_ops_gauges()
    disk_issue = check_and_alert_disk()
    result = {
        "status": "ok" if not disk_issue else "alert",
        "issues": [disk_issue] if disk_issue else [],
        "beat_last_ok": (
            snap["beat_last_ok"].isoformat() if snap["beat_last_ok"] else None
        ),
        "disk_free_bytes": snap["disk_free_bytes"],
    }
    logger.info("ops_health_check %s", result)
    return result
