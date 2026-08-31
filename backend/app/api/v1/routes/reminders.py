"""Маршруты напоминаний."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_reminder_service
from app.api.v1.schemas.reminder_schema import ReminderCreateRequest, ReminderListResponse, ReminderResponse
from app.services.dto.reminder_dto import ReminderCreateDTO
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/v1/reminders", tags=["Reminders"])


@router.post("")
def create_reminder(
    body: ReminderCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: ReminderService = Depends(get_reminder_service),
) -> dict:
    dto = ReminderCreateDTO(charge_id=body.charge_id, reminder_type=body.reminder_type)
    result = service.create_reminder(account_id, dto)
    return {"status": "success", "data": ReminderResponse.model_validate(result).model_dump()}


@router.get("/{charge_id}", response_model=ReminderListResponse)
def get_reminders(
    charge_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ReminderService = Depends(get_reminder_service),
) -> dict:
    reminders = service.get_reminders(charge_id, account_id)
    return {"status": "success", "data": [ReminderResponse.model_validate(r) for r in reminders]}