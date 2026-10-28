from app.scripts.check_celery_beat_health import is_celery_beat_running
from app.scripts.check_outbox_relay_health import is_outbox_relay_healthy


def test_celery_beat_process_healthcheck_matches_only_beat_process(tmp_path):
    beat_process = tmp_path / "123"
    beat_process.mkdir()
    (beat_process / "cmdline").write_bytes(
        b"/usr/local/bin/python\x00-m\x00celery\x00-A\x00"
        b"worker.celery_app\x00beat\x00--loglevel=info\x00"
    )

    worker_process = tmp_path / "124"
    worker_process.mkdir()
    (worker_process / "cmdline").write_bytes(
        b"/usr/local/bin/python\x00-m\x00celery\x00-A\x00"
        b"worker.celery_app\x00worker\x00"
    )

    assert is_celery_beat_running(proc_root=tmp_path, current_pid=999)
    assert not is_celery_beat_running(proc_root=tmp_path, current_pid=123)


def test_outbox_relay_healthcheck_requires_a_fresh_heartbeat():
    class RedisStub:
        def __init__(self, value):
            self.value = value

        def get(self, _key):
            return self.value

    assert is_outbox_relay_healthy(RedisStub(b"190"), now=200, max_age_seconds=20)
    assert not is_outbox_relay_healthy(RedisStub(b"100"), now=200, max_age_seconds=20)
    assert not is_outbox_relay_healthy(RedisStub(None), now=200, max_age_seconds=20)
    assert not is_outbox_relay_healthy(RedisStub(b"bad"), now=200, max_age_seconds=20)
