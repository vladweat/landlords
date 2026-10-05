"""Проверки ops и отправка алертов (email + Sentry) с дедупом."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.ops_heartbeat import get_beat_last_ok, try_acquire_alert_dedup

try:
    from prometheus_client import Gauge

    OPS_BEAT_LAST_OK = Gauge(
        "ops_beat_last_ok_timestamp",
        "Unix timestamp of last successful Celery beat scheduled task",
    )
    OPS_DISK_FREE = Gauge(
        "ops_documents_disk_free_bytes",
        "Free bytes on documents storage volume",
    )
except Exception:  # pragma: no cover
    OPS_BEAT_LAST_OK = None
    OPS_DISK_FREE = None


def update_ops_gauges() -> dict[str, Any]:
    """Обновить Prometheus gauges и вернуть снимок состояния."""
    last_ok = get_beat_last_ok()
    beat_ts = last_ok.timestamp() if last_ok else 0.0
    if OPS_BEAT_LAST_OK is not None:
        OPS_BEAT_LAST_OK.set(beat_ts)

    free: int | None = None
    try:
        Path(settings.DOCUMENTS_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(settings.DOCUMENTS_STORAGE_DIR).free
        if OPS_DISK_FREE is not None:
            OPS_DISK_FREE.set(free)
    except Exception:
        logger.exception("disk_usage failed")

    return {"beat_last_ok": last_ok, "disk_free_bytes": free}


def send_ops_alert(subject: str, body: str, sentry_level: str = "error") -> None:
    """Письмо на SUPPORT_EMAIL + capture_message в Sentry."""
    if settings.SUPPORT_EMAIL:
        try:
            EmailService().send(
                to=settings.SUPPORT_EMAIL, subject=subject, body_text=body
            )
        except Exception:
            logger.exception("Failed to send ops alert email")
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk

            sentry_sdk.capture_message(f"{subject}: {body}", level=sentry_level)
        except Exception:
            logger.exception("Failed Sentry capture_message for ops alert")


def check_and_alert_beat_stale() -> str | None:
    """
    Если heartbeat beat старше порога — алерт (с дедупом).
    Вызывать из /ready: beat-задача сама не сработает, если beat мёртв.
    """
    last_ok = get_beat_last_ok()
    now = datetime.now(timezone.utc)
    if last_ok is None:
        # Нет метки: после деплоя нормально; алертим только если ключ пропал надолго —
        # без метки не спамим (cold start).
        return None
    age_h = (now - last_ok).total_seconds() / 3600
    if age_h <= settings.OPS_BEAT_STALE_HOURS:
        return None
    issue = f"beat_stale age_hours={age_h:.1f} threshold={settings.OPS_BEAT_STALE_HOURS}"
    if try_acquire_alert_dedup("beat_stale", ttl_seconds=3600):
        send_ops_alert(
            subject="[Landlords] Ops alert: beat_stale",
            body=(
                f"Issue: {issue}\n"
                f"Time: {now.isoformat()}\n"
                f"Env: {settings.APP_ENV}\n"
                f"Last ok: {last_ok.isoformat()}\n"
            ),
        )
    return issue


def check_and_alert_disk() -> str | None:
    """Мало места под документы — алерт с дедупом."""
    snap = update_ops_gauges()
    free = snap["disk_free_bytes"]
    now = datetime.now(timezone.utc)
    if free is None:
        issue = "documents_disk_unreadable"
        if try_acquire_alert_dedup(issue, ttl_seconds=3600):
            send_ops_alert(
                subject="[Landlords] Ops alert: documents_disk_unreadable",
                body=f"Issue: {issue}\nTime: {now.isoformat()}\nEnv: {settings.APP_ENV}\n",
            )
        return issue
    min_bytes = settings.OPS_DISK_MIN_FREE_MB * 1024 * 1024
    if free >= min_bytes:
        return None
    free_mb = free / (1024 * 1024)
    issue = f"documents_disk_low free_mb={free_mb:.0f} min_mb={settings.OPS_DISK_MIN_FREE_MB}"
    if try_acquire_alert_dedup("documents_disk_low", ttl_seconds=3600):
        send_ops_alert(
            subject="[Landlords] Ops alert: documents_disk_low",
            body=(
                f"Issue: {issue}\n"
                f"Time: {now.isoformat()}\n"
                f"Env: {settings.APP_ENV}\n"
                f"Path: {settings.DOCUMENTS_STORAGE_DIR}\n"
            ),
        )
    return issue
