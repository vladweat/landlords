"""Публичный статус сервиса из JSON-файла."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings

DEFAULT_STATUS: dict[str, Any] = {
    "overall": "operational",
    "updated_at": None,
    "support_email": None,
    "incidents": [],
}


class StatusService:
    """Читает storage/status/incidents.json (правка без редеплоя)."""

    def get_public_status(self) -> dict[str, Any]:
        """Статус для публичного API."""
        path = Path(settings.STATUS_INCIDENTS_PATH)
        data = dict(DEFAULT_STATUS)
        data["support_email"] = settings.SUPPORT_EMAIL
        data["status_url"] = f"{settings.FRONTEND_URL.rstrip('/')}/status"

        if path.is_file():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    overall = raw.get("overall", "operational")
                    if overall not in ("operational", "degraded", "outage"):
                        overall = "operational"
                    data["overall"] = overall
                    data["updated_at"] = raw.get("updated_at") or data["updated_at"]
                    incidents = raw.get("incidents") or []
                    if isinstance(incidents, list):
                        data["incidents"] = incidents
            except Exception:
                logger.exception("Failed to read status file path={}", path)
                data["overall"] = "degraded"
                data["incidents"] = [
                    {
                        "id": "status-file-error",
                        "title": "Не удалось прочитать файл статуса",
                        "status": "investigating",
                        "started_at": datetime.now(timezone.utc).isoformat(),
                        "message": "Обратитесь в поддержку, если страница долго недоступна.",
                    }
                ]
        else:
            data["updated_at"] = data["updated_at"] or datetime.now(timezone.utc).isoformat()

        if not data.get("updated_at"):
            data["updated_at"] = datetime.now(timezone.utc).isoformat()
        return data
