"""Схемы для напоминаний."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReminderCreateRequest(BaseModel):
    charge_id: UUID
    reminder_type: str


class ReminderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    charge_id: UUID
    reminder_type: str
    message_text: str
    created_at: datetime


class ReminderListResponse(BaseModel):
    status: str = "success"
    data: list[ReminderResponse]