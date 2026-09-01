"""Redis-based distributed lock for Celery bulk tasks."""
from __future__ import annotations

from typing import Optional

import redis

from app.core.config import settings


class RedisLock:
    """
    Simple context-manager wrapper around redis-py's Lock.

    Usage:
        with RedisLock("update_overdue_charges", ttl=600):
            # do work
    If the lock cannot be acquired immediately, a RuntimeError is raised.
    """

    def __init__(self, name: str, ttl: int = 600) -> None:
        self.name = f"locks:{name}"
        self.ttl = ttl
        self._client: Optional[redis.Redis] = None
        self._lock: Optional[redis.lock.Lock] = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(settings.REDIS_URL)
        return self._client

    def __enter__(self) -> redis.lock.Lock:
        self._lock = self.client.lock(self.name, timeout=self.ttl)
        acquired = self._lock.acquire(blocking=False)
        if not acquired:
            raise RuntimeError("lock_not_acquired")
        return self._lock

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self._lock and self._lock.owned():
                self._lock.release()
        except Exception:
            # best-effort release; swallow to avoid masking original exceptions
            pass

    # Convenience methods for manual acquire/release (non-blocking)
    def try_acquire(self) -> bool:
        """Try to acquire lock without blocking. Returns True if acquired."""
        self._lock = self.client.lock(self.name, timeout=self.ttl)
        return self._lock.acquire(blocking=False)

    def release(self) -> None:
        try:
            if self._lock and self._lock.owned():
                self._lock.release()
        except Exception:
            pass

