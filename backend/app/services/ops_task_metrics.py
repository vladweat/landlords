"""Low-cardinality Celery and relay telemetry stored in Redis."""

from __future__ import annotations

from functools import lru_cache
import time
from typing import Callable

import redis
from loguru import logger
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from app.core.config import settings

TASK_LABELS = {
    "app.tasks.charge_tasks.generate_charges_for_contract": "generate_charges_for_contract",
    "app.tasks.charge_tasks.update_overdue_charges": "update_overdue_charges",
    "app.tasks.email_tasks.send_daily_reminder_emails": "send_daily_reminder_emails",
    "app.tasks.billing_tasks.process_subscription_renewals": "process_subscription_renewals",
    "app.tasks.ops_tasks.check_ops_health": "check_ops_health",
    "app.tasks.payment_idempotency_tasks.cleanup_expired_payment_idempotency_records": (
        "cleanup_expired_payment_idempotency_records"
    ),
}
TASK_STATUSES = ("started", "success", "failure", "skipped")
METRICS_RETENTION_SECONDS = 31_536_000
RELAY_HEARTBEAT_TTL_SECONDS = 120
TASK_METRICS_PREFIX = f"{settings.REDIS_KEY_PREFIX}ops:celery_task:"
OUTBOX_TERMINAL_FAILURE_KEY = f"{settings.REDIS_KEY_PREFIX}ops:outbox:terminal_failures"
OUTBOX_RELAY_HEARTBEAT_KEY = f"{settings.REDIS_KEY_PREFIX}ops:outbox_relay:last_poll"


def task_metrics_key(task_label: str) -> str:
    """Build a key only from a known fixed task label."""
    return f"{TASK_METRICS_PREFIX}{task_label}"


@lru_cache(maxsize=1)
def _client() -> redis.Redis:
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def record_task_event(
    task_name: str,
    status: str,
    *,
    timestamp: float | None = None,
    redis_client=None,
) -> None:
    """Increment one known task event; telemetry failures never affect tasks."""
    task_label = TASK_LABELS.get(task_name)
    if task_label is None or status not in TASK_STATUSES:
        return
    now = time.time() if timestamp is None else timestamp
    key = task_metrics_key(task_label)
    try:
        client = redis_client or _client()
        client.hincrby(key, f"{status}_total", 1)
        client.hset(key, f"last_{status}", now)
        client.expire(key, METRICS_RETENTION_SECONDS)
    except Exception:
        logger.warning("celery_task_metric_write_failed task_name={}", task_label)


def record_outbox_terminal_failure(*, redis_client=None) -> None:
    """Increment the terminal outbox failure counter without storing row IDs."""
    try:
        client = redis_client or _client()
        client.hincrby(OUTBOX_TERMINAL_FAILURE_KEY, "total", 1)
        client.expire(OUTBOX_TERMINAL_FAILURE_KEY, METRICS_RETENTION_SECONDS)
    except Exception:
        logger.warning("outbox_terminal_failure_metric_write_failed")


def mark_outbox_relay_heartbeat(
    *, timestamp: float | None = None, redis_client=None
) -> None:
    """Store a short-lived timestamp so a stopped relay becomes visibly stale."""
    now = time.time() if timestamp is None else timestamp
    try:
        client = redis_client or _client()
        client.set(OUTBOX_RELAY_HEARTBEAT_KEY, now, ex=RELAY_HEARTBEAT_TTL_SECONDS)
    except Exception:
        logger.warning("outbox_relay_heartbeat_write_failed")


def _float(value: object) -> float:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


class OpsTaskMetricsCollector:
    """Expose Redis snapshots as fixed-name Prometheus metric families."""

    def __init__(self, client_factory: Callable[[], object] | None = None) -> None:
        self.client_factory = client_factory or _client

    def collect(self):
        available = 1
        task_rows: dict[str, dict] = {}
        terminal_failures = 0.0
        relay_last_poll = 0.0
        try:
            client = self.client_factory()
            for task_name, task_label in TASK_LABELS.items():
                task_rows[task_label] = client.hgetall(task_metrics_key(task_label))
            terminal_failures = _float(
                client.hget(OUTBOX_TERMINAL_FAILURE_KEY, "total")
            )
            relay_last_poll = _float(client.get(OUTBOX_RELAY_HEARTBEAT_KEY))
        except Exception:
            available = 0

        events = CounterMetricFamily(
            "landlords_celery_task_events",
            "Celery task event totals from the Redis ops snapshot",
            labels=["task_name", "status"],
        )
        last_event = GaugeMetricFamily(
            "landlords_celery_task_last_event_timestamp_seconds",
            "Unix timestamp of the most recent Celery task event",
            labels=["task_name", "event"],
        )
        for task_label in TASK_LABELS.values():
            row = task_rows.get(task_label, {})
            for status in TASK_STATUSES:
                events.add_metric(
                    [task_label, status], _float(row.get(f"{status}_total"))
                )
                last_event.add_metric(
                    [task_label, status], _float(row.get(f"last_{status}"))
                )

        outbox_failures = CounterMetricFamily(
            "landlords_outbox_terminal_failures",
            "Outbox charge tasks that entered terminal failure",
        )
        outbox_failures.add_metric([], terminal_failures)
        relay_heartbeat = GaugeMetricFamily(
            "landlords_outbox_relay_last_poll_timestamp_seconds",
            "Unix timestamp of the last outbox relay poll iteration",
        )
        relay_heartbeat.add_metric([], relay_last_poll)
        telemetry_available = GaugeMetricFamily(
            "landlords_ops_telemetry_redis_available",
            "Whether Redis ops telemetry could be read",
        )
        telemetry_available.add_metric([], available)
        yield events
        yield last_event
        yield outbox_failures
        yield relay_heartbeat
        yield telemetry_available
