"""Heartbeat Celery beat и чтение ops-метрик из Redis."""

from __future__ import annotations

from datetime import datetime, timezone

import redis
from loguru import logger

from app.core.config import settings

BEAT_LAST_OK_KEY = "ops:beat:last_ok"
ALERT_DEDUP_PREFIX = "ops:alert:dedup:"


def _client() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL)


def mark_beat_ok() -> None:
    """Записать метку успешного выполнения scheduled-задачи."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        _client().set(BEAT_LAST_OK_KEY, now)
    except Exception:
        logger.exception("Failed to write beat heartbeat")


def get_beat_last_ok() -> datetime | None:
    """Вернуть время последнего успешного beat heartbeat или None."""
    try:
        raw = _client().get(BEAT_LAST_OK_KEY)
    except Exception:
        logger.exception("Failed to read beat heartbeat")
        return None
    if not raw:
        return None
    text = raw.decode() if isinstance(raw, bytes) else str(raw)
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def try_acquire_alert_dedup(alert_key: str, ttl_seconds: int = 3600) -> bool:
    """True, если алерт ещё не слали недавно (SET NX)."""
    try:
        return bool(
            _client().set(f"{ALERT_DEDUP_PREFIX}{alert_key}", "1", nx=True, ex=ttl_seconds)
        )
    except Exception:
        logger.exception("Failed alert dedup for {}", alert_key)
        return True
