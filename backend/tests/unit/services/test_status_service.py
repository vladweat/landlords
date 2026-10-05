"""Тесты StatusService."""

import json
from pathlib import Path

from app.core.config import settings
from app.services.status_service import StatusService


def test_status_from_file(tmp_path: Path, monkeypatch):
    path = tmp_path / "incidents.json"
    path.write_text(
        json.dumps(
            {
                "overall": "degraded",
                "updated_at": "2026-10-05T12:00:00+00:00",
                "incidents": [
                    {
                        "id": "1",
                        "title": "SMTP",
                        "status": "investigating",
                        "started_at": "2026-10-05T11:00:00+00:00",
                        "message": "Письма задерживаются",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "STATUS_INCIDENTS_PATH", str(path))
    monkeypatch.setattr(settings, "SUPPORT_EMAIL", "ops@example.com")

    data = StatusService().get_public_status()
    assert data["overall"] == "degraded"
    assert data["support_email"] == "ops@example.com"
    assert len(data["incidents"]) == 1
    assert data["incidents"][0]["title"] == "SMTP"


def test_status_missing_file_defaults_operational(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "STATUS_INCIDENTS_PATH", str(tmp_path / "missing.json"))
    data = StatusService().get_public_status()
    assert data["overall"] == "operational"
    assert data["incidents"] == []
