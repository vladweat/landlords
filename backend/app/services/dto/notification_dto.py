"""DTO уведомлений (inbox внимания)."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NotificationItemDTO(BaseModel):
    """Элемент inbox: просрочка или окончание договора."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: Literal["charge_overdue", "contract_ending"]
    title: str
    body: str
    severity: Literal["warning", "critical"]
    href: str
    created_at: date
    meta: dict[str, Any] = Field(default_factory=dict)


class NotificationListDTO(BaseModel):
    """Список уведомлений с счётчиком непрочитанных."""

    items: list[NotificationItemDTO] = Field(default_factory=list)
    unread_count: int = 0


class NotificationDismissDTO(BaseModel):
    """Запрос на скрытие уведомления."""

    notification_key: str = Field(..., min_length=1, max_length=120)
