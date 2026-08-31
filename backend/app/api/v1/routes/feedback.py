"""Маршруты для обратной связи."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_current_user_id, get_feedback_service
from app.api.v1.schemas.feedback_schema import FeedbackCreateRequest
from app.services.dto.feedback_dto import FeedbackCreateDTO
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/v1/feedback", tags=["Feedback"])


@router.post("")
def create_feedback(
    body: FeedbackCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: FeedbackService = Depends(get_feedback_service),
) -> dict:
    """Отправить сообщение обратной связи."""
    dto = FeedbackCreateDTO.model_validate(body.model_dump())
    result = service.create_feedback(account_id, user_id, dto)
    return {"status": "success", "data": result.model_dump()}
