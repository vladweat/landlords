"""Healthcheck свежести heartbeat outbox relay в Redis."""

from __future__ import annotations

import time

import redis

from app.core.config import settings
from app.services.ops_task_metrics import OUTBOX_RELAY_HEARTBEAT_KEY


def is_outbox_relay_healthy(
    client=None,
    *,
    now: float | None = None,
    max_age_seconds: int = 120,
) -> bool:
    """Вернуть False при отсутствующем, устаревшем или нечитаемом heartbeat."""
    try:
        client = client or redis.Redis.from_url(settings.REDIS_URL)
        value = client.get(OUTBOX_RELAY_HEARTBEAT_KEY)
        if value is None:
            return False
        if isinstance(value, bytes):
            value = value.decode("ascii")
        age = (time.time() if now is None else now) - float(value)
        return 0 <= age <= max_age_seconds
    except Exception:
        return False


def main() -> None:
    raise SystemExit(0 if is_outbox_relay_healthy() else 1)


if __name__ == "__main__":
    main()
