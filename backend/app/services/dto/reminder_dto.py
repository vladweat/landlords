"""DTO для напоминаний."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ReminderCreateDTO(BaseModel):
    charge_id: UUID
    reminder_type: str  # first, second, third


class ReminderDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    account_id: UUID
    contract_id: UUID
    charge_id: UUID
    reminder_type: str
    message_text: str
    created_at: datetime