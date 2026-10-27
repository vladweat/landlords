from app.tasks.lock import RedisLock


class FakeLock:
    def __init__(self, name, timeout=None):
        self._owned = False

    def acquire(self, blocking=False):
        # simulate already acquired by another process
        return False

    def owned(self):
        return self._owned

    def release(self):
        self._owned = False


class FakeRedis:
    def lock(self, name, timeout=None):
        assert name.startswith("landlords:locks:")
        return FakeLock(name, timeout=timeout)


def test_redislock_try_acquire(monkeypatch):
    # ensure try_acquire returns False when lock is held elsewhere
    monkeypatch.setattr("app.tasks.lock.redis.from_url", lambda url: FakeRedis())
    lock = RedisLock("test_lock", ttl=10)
    assert lock.try_acquire() is False

