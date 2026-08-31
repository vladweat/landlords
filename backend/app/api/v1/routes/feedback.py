"""Маршруты для обратной связи."""

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_account_id, get_current_user_id
from app.api.v1.schemas.feedback_schema import FeedbackCreateRequest
from app.db.models.feedback_model import FeedbackModel
from app.db.session import get_db_session

router = APIRouter(prefix="/v1/feedback", tags=["Feedback"])


@router.post("")
def create_feedback(
    body: FeedbackCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    session: Session = Depends(get_db_session),
) -> dict:
    """Отправить сообщение обратной связи."""
    fb = FeedbackModel(
        id=uuid4(),
        account_id=account_id,
        user_id=user_id,
        category=body.category,
        message=body.message,
    )
    session.add(fb)
    session.flush()
    return {
        "status": "success",
        "data": {
            "id": str(fb.id),
            "message": "Спасибо! Мы получили ваше сообщение.",
        },
    }