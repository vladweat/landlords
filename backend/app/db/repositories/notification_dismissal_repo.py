"""Реализация репозитория скрытых уведомлений."""

from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models.notification_dismissal_model import NotificationDismissalModel
from app.domain.entities import NotificationDismissalEntity
from app.domain.interfaces import INotificationDismissalRepository


class NotificationDismissalRepository(INotificationDismissalRepository):
    """Реализация репозитория скрытых уведомлений на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_keys(self, account_id: UUID, user_id: UUID) -> set[str]:
        rows = (
            self.session.query(NotificationDismissalModel.notification_key)
            .filter(
                NotificationDismissalModel.account_id == account_id,
                NotificationDismissalModel.user_id == user_id,
            )
            .all()
        )
        return {row[0] for row in rows}

    def dismiss(
        self, entity: NotificationDismissalEntity
    ) -> NotificationDismissalEntity:
        stmt = (
            insert(NotificationDismissalModel)
            .values(
                id=entity.id,
                account_id=entity.account_id,
                user_id=entity.user_id,
                notification_key=entity.notification_key,
                dismissed_at=entity.dismissed_at,
            )
            .on_conflict_do_nothing(
                constraint="uq_notification_dismissals_key",
            )
            .returning(NotificationDismissalModel)
        )
        result = self.session.execute(stmt).scalar_one_or_none()
        self.session.flush()
        if result is not None:
            return result.to_entity()
        existing = (
            self.session.query(NotificationDismissalModel)
            .filter(
                NotificationDismissalModel.account_id == entity.account_id,
                NotificationDismissalModel.user_id == entity.user_id,
                NotificationDismissalModel.notification_key == entity.notification_key,
            )
            .one()
        )
        return existing.to_entity()
