"""Gated live Redis ACL checks; run only after the Redis ACL rollout."""

import os
from uuid import uuid4

import pytest
import redis
from redis.exceptions import AuthenticationError, ResponseError

from app.core.config import settings


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_REDIS_ACL_TESTS") != "true",
    reason="requires the explicitly activated Redis ACL configuration",
)


def test_default_and_invalid_credentials_are_rejected():
    unauthenticated = redis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB
    )
    invalid = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        username=settings.REDIS_USERNAME,
        password="deliberately-invalid-redis-password",
    )
    try:
        with pytest.raises(AuthenticationError):
            unauthenticated.ping()
        with pytest.raises(AuthenticationError):
            invalid.ping()
    finally:
        unauthenticated.close()
        invalid.close()


def test_current_identity_is_limited_to_its_key_and_command_scope():
    client = redis.Redis.from_url(settings.REDIS_URL)
    suffix = uuid4().hex
    is_api = settings.REDIS_USERNAME == "landlords_api"
    if is_api:
        allowed_key = f"{settings.REDIS_KEY_PREFIX}ops:acl-smoke:{suffix}"
        denied_key = f"{settings.REDIS_KEY_PREFIX}celery:acl-smoke:{suffix}"
    else:
        allowed_key = f"{settings.REDIS_KEY_PREFIX}acl-smoke:{suffix}"
        denied_key = f"outside:acl-smoke:{suffix}"
    try:
        assert client.ping()
        client.set(allowed_key, "ok", ex=30)
        assert client.get(allowed_key) == b"ok"
        with pytest.raises(ResponseError):
            client.set(denied_key, "must-not-be-written", ex=30)
        with pytest.raises(ResponseError):
            client.config_get("*")
        if is_api:
            with pytest.raises(ResponseError):
                client.publish(f"{settings.REDIS_KEY_PREFIX}acl-smoke", "probe")
        else:
            channel_prefix = settings.REDIS_KEY_PREFIX
            allowed_subscription = client.pubsub()
            try:
                allowed_patterns = [f"{channel_prefix}/0.celery.pidbox"]
                allowed_patterns.append(f"{channel_prefix}celery-task-meta-*")
                if settings.REDIS_USERNAME == "landlords_worker":
                    event_channel = f"{channel_prefix}/0.celeryev/worker.acl-smoke-{suffix}"
                    client.publish(event_channel, "probe")
                    client.publish(f"{channel_prefix}celery-task-meta-acl-smoke-{suffix}", "probe")
                    allowed_patterns.append(f"{channel_prefix}/0.celeryev/worker.*")
                else:
                    allowed_patterns.append(f"{channel_prefix}/0.celeryev/*")
                with pytest.raises(ResponseError):
                    client.publish(f"outside:acl-smoke:{suffix}", "probe")
                for pattern in allowed_patterns:
                    allowed_subscription.psubscribe(pattern)
                    message = allowed_subscription.get_message(timeout=1)
                    assert message is not None
                    assert message["type"] == "psubscribe"
            finally:
                allowed_subscription.close()

            denied_subscription = client.pubsub()
            try:
                denied_pattern = (
                    f"{channel_prefix}/0.celeryev/beat.*"
                    if settings.REDIS_USERNAME == "landlords_worker"
                    else f"{channel_prefix}/0.celeryev/#"
                )
                denied_subscription.psubscribe(denied_pattern)
                with pytest.raises(ResponseError):
                    denied_subscription.get_message(timeout=1)
            finally:
                denied_subscription.close()
    finally:
        client.delete(allowed_key)
        client.close()
