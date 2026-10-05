"""Тесты ops alert helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from app.core.config import settings
from app.services import ops_alert_service


def test_check_beat_stale_none_when_fresh(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "OPS_BEAT_STALE_HOURS", 26)
    with patch.object(
        ops_alert_service, "get_beat_last_ok", return_value=now - timedelta(hours=1)
    ):
        assert ops_alert_service.check_and_alert_beat_stale() is None


def test_check_beat_stale_alerts_when_old(monkeypatch):
    now = datetime.now(timezone.utc)
    monkeypatch.setattr(settings, "OPS_BEAT_STALE_HOURS", 26)
    monkeypatch.setattr(settings, "SUPPORT_EMAIL", "ops@example.com")
    monkeypatch.setattr(settings, "SENTRY_DSN", None)
    with (
        patch.object(
            ops_alert_service,
            "get_beat_last_ok",
            return_value=now - timedelta(hours=40),
        ),
        patch.object(ops_alert_service, "try_acquire_alert_dedup", return_value=True),
        patch.object(ops_alert_service, "send_ops_alert") as send,
    ):
        issue = ops_alert_service.check_and_alert_beat_stale()
        assert issue is not None
        assert "beat_stale" in issue
        send.assert_called_once()


def test_check_disk_alerts_when_low(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DOCUMENTS_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "OPS_DISK_MIN_FREE_MB", 10**12)  # невозможно
    monkeypatch.setattr(settings, "SUPPORT_EMAIL", "ops@example.com")
    monkeypatch.setattr(settings, "SENTRY_DSN", None)
    with (
        patch.object(ops_alert_service, "try_acquire_alert_dedup", return_value=True),
        patch.object(ops_alert_service, "send_ops_alert") as send,
    ):
        issue = ops_alert_service.check_and_alert_disk()
        assert issue is not None
        assert "documents_disk_low" in issue
        send.assert_called_once()
