from types import SimpleNamespace
from app.services import ops_task_metrics


class FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.strings = {}
        self.expirations = {}

    def hincrby(self, key, field, amount):
        current = int(self.hashes.setdefault(key, {}).get(field, 0))
        self.hashes[key][field] = current + amount
        return current + amount

    def hset(self, key, field=None, value=None, mapping=None):
        values = mapping or {field: value}
        self.hashes.setdefault(key, {}).update(values)

    def hgetall(self, key):
        return self.hashes.get(key, {}).copy()

    def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)

    def expire(self, key, seconds):
        self.expirations[key] = seconds
        return True

    def set(self, key, value, ex=None):
        self.strings[key] = value
        self.expirations[key] = ex
        return True

    def get(self, key):
        return self.strings.get(key)


def test_records_fixed_task_events_and_refreshes_retention():
    client = FakeRedis()

    ops_task_metrics.record_task_event(
        "app.tasks.charge_tasks.update_overdue_charges",
        "started",
        timestamp=100,
        redis_client=client,
    )
    ops_task_metrics.record_task_event(
        "app.tasks.charge_tasks.update_overdue_charges",
        "skipped",
        timestamp=101,
        redis_client=client,
    )

    snapshot = client.hgetall(ops_task_metrics.task_metrics_key("update_overdue_charges"))
    assert snapshot["started_total"] == 1
    assert snapshot["skipped_total"] == 1
    assert snapshot["last_started"] == 100
    assert snapshot["last_skipped"] == 101
    assert client.expirations[ops_task_metrics.task_metrics_key("update_overdue_charges")] == 31_536_000


def test_unknown_task_names_and_statuses_do_not_create_metric_series():
    client = FakeRedis()

    ops_task_metrics.record_task_event("plugin.unbounded_task", "success", redis_client=client)
    ops_task_metrics.record_task_event(
        "app.tasks.charge_tasks.update_overdue_charges", "arbitrary", redis_client=client
    )

    assert client.hashes == {}


def test_task_signal_callbacks_record_skip_and_failure_once(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(ops_task_metrics, "_client", lambda: client)
    from app.celery_app import _on_task_failure, _on_task_postrun

    task = SimpleNamespace(name="app.tasks.email_tasks.send_daily_reminder_emails")
    _on_task_postrun(
        sender=task,
        task_id="must-not-be-stored",
        task=task,
        retval={"status": "skipped"},
        state="SUCCESS",
    )
    _on_task_failure(
        sender=task,
        task_id="must-not-be-stored",
        exception=RuntimeError("private message"),
    )
    _on_task_postrun(
        sender=task,
        task_id="must-not-be-stored",
        task=task,
        retval=None,
        state="FAILURE",
    )

    snapshot = client.hgetall(ops_task_metrics.task_metrics_key("send_daily_reminder_emails"))
    assert snapshot["skipped_total"] == 1
    assert snapshot["failure_total"] == 1
    assert "must-not-be-stored" not in repr(client.hashes)
    assert "private message" not in repr(client.hashes)


def test_task_recording_is_best_effort_when_redis_is_unavailable():
    class BrokenRedis:
        def hincrby(self, *_args):
            raise ConnectionError("redis unavailable")

    ops_task_metrics.record_task_event(
        "app.tasks.ops_tasks.check_ops_health", "started", redis_client=BrokenRedis()
    )


def test_collector_uses_only_fixed_labels_and_emits_relay_heartbeat():
    client = FakeRedis()
    ops_task_metrics.record_task_event(
        "app.tasks.billing_tasks.process_subscription_renewals",
        "success",
        timestamp=200,
        redis_client=client,
    )
    ops_task_metrics.mark_outbox_relay_heartbeat(timestamp=201, redis_client=client)
    ops_task_metrics.record_outbox_terminal_failure(redis_client=client)
    collector = ops_task_metrics.OpsTaskMetricsCollector(lambda: client)

    metrics = {metric.name: metric for metric in collector.collect()}

    assert "landlords_celery_task_events" in metrics
    samples = metrics["landlords_celery_task_events"].samples
    assert any(
        sample.labels == {"task_name": "process_subscription_renewals", "status": "success"}
        and sample.value == 1
        for sample in samples
    )
    heartbeat = metrics["landlords_outbox_relay_last_poll_timestamp_seconds"].samples[0]
    assert heartbeat.value == 201
    assert metrics["landlords_outbox_terminal_failures"].samples[0].value == 1
    assert client.expirations[ops_task_metrics.OUTBOX_RELAY_HEARTBEAT_KEY] == 120
    assert all("account_id" not in sample.labels for metric in metrics.values() for sample in metric.samples)


def test_collector_reports_redis_unavailable_without_failing_scrape():
    class BrokenRedis:
        def hgetall(self, *_args):
            raise ConnectionError("redis unavailable")

    collector = ops_task_metrics.OpsTaskMetricsCollector(lambda: BrokenRedis())

    metrics = {metric.name: metric for metric in collector.collect()}

    assert metrics["landlords_ops_telemetry_redis_available"].samples[0].value == 0
    assert metrics["landlords_outbox_relay_last_poll_timestamp_seconds"].samples[0].value == 0


def test_terminal_outbox_failures_are_counted_in_redis():
    client = FakeRedis()

    ops_task_metrics.record_outbox_terminal_failure(redis_client=client)
    ops_task_metrics.record_outbox_terminal_failure(redis_client=client)

    assert client.hashes[ops_task_metrics.OUTBOX_TERMINAL_FAILURE_KEY]["total"] == 2
