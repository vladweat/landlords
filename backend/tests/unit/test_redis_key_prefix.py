from app.celery_app import celery_app
from app.services.ops_heartbeat import ALERT_DEDUP_PREFIX, BEAT_LAST_OK_KEY


def test_celery_and_ops_keys_share_restrictable_redis_prefix():
    assert BEAT_LAST_OK_KEY.startswith("landlords:")
    assert ALERT_DEDUP_PREFIX.startswith("landlords:")
    assert (
        celery_app.conf.broker_transport_options["global_keyprefix"]
        == "landlords:"
    )
    assert (
        celery_app.conf.result_backend_transport_options["global_keyprefix"]
        == "landlords:"
    )
