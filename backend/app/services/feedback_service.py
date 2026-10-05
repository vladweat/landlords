"""Сервис обратной связи."""

from uuid import UUID, uuid4

from loguru import logger

from app.core.config import settings
from app.domain.entities import FeedbackEntity
from app.domain.interfaces import IFeedbackRepository
from app.services.dto.feedback_dto import FeedbackCreateDTO, FeedbackDTO
from app.services.email_service import EmailService


class FeedbackService:
    """Сервис для создания сообщений обратной связи."""

    def __init__(
        self,
        repo: IFeedbackRepository,
        email_service: EmailService | None = None,
    ) -> None:
        self.repo = repo
        self.email_service = email_service or EmailService()

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
        self._notify_support(created)
        return FeedbackDTO(
            id=str(created.id),
            message="Спасибо! Мы получили ваше сообщение.",
        )

    def _notify_support(self, entity: FeedbackEntity) -> None:
        to = settings.SUPPORT_EMAIL
        if not to:
            return
        try:
            self.email_service.send(
                to=to,
                subject=f"[Landlords] Обратная связь: {entity.category}",
                body_text=(
                    f"Категория: {entity.category}\n"
                    f"Account: {entity.account_id}\n"
                    f"User: {entity.user_id}\n"
                    f"Feedback id: {entity.id}\n\n"
                    f"{entity.message}\n"
                ),
            )
        except Exception:
            logger.exception("Failed to email support about feedback id={}", entity.id)
