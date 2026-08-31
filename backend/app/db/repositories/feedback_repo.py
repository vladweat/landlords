"""Реализация репозитория обратной связи."""

from sqlalchemy.orm import Session

from app.db.models.feedback_model import FeedbackModel
from app.domain.entities import FeedbackEntity
from app.domain.interfaces import IFeedbackRepository


class FeedbackRepository(IFeedbackRepository):
    """Реализация репозитория обратной связи на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: FeedbackEntity) -> FeedbackEntity:
        model = FeedbackModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()
