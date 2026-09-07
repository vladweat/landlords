"""Pydantic-схемы UI-уведомлений."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationItemResponse(BaseModel):
    """Элемент inbox в ответе API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: Literal["charge_overdue", "contract_ending"]
    title: str
    body: str
    severity: Literal["warning", "critical"]
    href: str
    created_at: date
    meta: dict[str, Any] = Field(default_factory=dict)


class NotificationListData(BaseModel):
    items: list[NotificationItemResponse] = Field(default_factory=list)
    unread_count: int = 0


class NotificationDismissRequest(BaseModel):
    notification_key: str = Field(..., min_length=1, max_length=120)
