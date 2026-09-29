"""Репозиторий лога email-уведомлений."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.db.models.email_dispatch_log_model import EmailDispatchLogModel
from app.domain.entities import EmailDispatchLogEntity
from app.domain.interfaces import IEmailDispatchLogRepository
from sqlalchemy.orm import Session


class EmailDispatchLogRepository(IEmailDispatchLogRepository):
    """SQLAlchemy-реализация лога отправок."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def was_sent_recently(
        self, account_id: UUID, notification_key: str, within_days: int
    ) -> bool:
        """True, если ключ уже отправляли за within_days дней."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
        row = (
            self.session.query(EmailDispatchLogModel)
            .filter_by(account_id=account_id, notification_key=notification_key)
            .filter(EmailDispatchLogModel.sent_at >= cutoff)
            .first()
        )
        return row is not None

    def record(self, entity: EmailDispatchLogEntity) -> EmailDispatchLogEntity:
        """Записать факт отправки (обновить sent_at при повторной записи)."""
        existing = (
            self.session.query(EmailDispatchLogModel)
            .filter_by(
                account_id=entity.account_id,
                notification_key=entity.notification_key,
            )
            .first()
        )
        now = datetime.now(timezone.utc)
        if existing:
            existing.sent_at = now
            self.session.flush()
            return existing.to_entity()
        model = EmailDispatchLogModel.from_entity(entity)
        model.sent_at = now
        self.session.add(model)
        self.session.flush()
        return model.to_entity()
