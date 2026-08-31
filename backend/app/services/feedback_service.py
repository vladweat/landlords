"""Сервис обратной связи."""

from uuid import UUID, uuid4

from app.domain.entities import FeedbackEntity
from app.domain.interfaces import IFeedbackRepository
from app.services.dto.feedback_dto import FeedbackCreateDTO, FeedbackDTO


class FeedbackService:
    """Сервис для создания сообщений обратной связи."""

    def __init__(self, repo: IFeedbackRepository) -> None:
        self.repo = repo

    def create_feedback(
        self, account_id: UUID, user_id: UUID, dto: FeedbackCreateDTO,
    ) -> FeedbackDTO:
        entity = FeedbackEntity(
            id=uuid4(),
            account_id=account_id,
            user_id=user_id,
            category=dto.category,
            message=dto.message,
        )
        created = self.repo.create(entity)
        return FeedbackDTO(
            id=str(created.id),
            message="Спасибо! Мы получили ваше сообщение.",
        )
