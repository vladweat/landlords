"""Маршруты UI-уведомлений."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import (
    get_current_account_id,
    get_current_user_id,
    get_notification_service,
)
from app.api.v1.schemas.notification_schema import (
    NotificationDismissRequest,
    NotificationItemResponse,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/v1/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Просрочки и окончания договоров, требующие внимания."""
    result = service.list_notifications(account_id, user_id)
    return {
        "status": "success",
        "data": {
            "items": [NotificationItemResponse.model_validate(i) for i in result.items],
            "unread_count": result.unread_count,
        },
    }


@router.post("/dismiss")
def dismiss_notification(
    body: NotificationDismissRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: NotificationService = Depends(get_notification_service),
) -> dict:
    """Скрыть уведомление из inbox текущего пользователя."""
    service.dismiss(account_id, user_id, body.notification_key)
    return {"status": "success", "data": {"dismissed": True}}
