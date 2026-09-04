"""Маршруты календаря платежей."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_calendar_service, get_current_account_id
from app.api.v1.schemas.calendar_schema import CalendarEventResponse
from app.services.calendar_service import CalendarService

router = APIRouter(prefix="/v1/calendar", tags=["Calendar"])


@router.get("/events")
def get_calendar_events(
    account_id: UUID = Depends(get_current_account_id),
    service: CalendarService = Depends(get_calendar_service),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
) -> dict:
    """Просрочки, ближайшие due dates и окончания договоров."""
    events = service.get_events(account_id, date_from=date_from, date_to=date_to)
    return {
        "status": "success",
        "data": {
            "items": [CalendarEventResponse.model_validate(e) for e in events],
        },
    }
