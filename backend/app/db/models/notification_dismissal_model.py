"""ORM-модель скрытых уведомлений пользователя."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import NotificationDismissalEntity


class NotificationDismissalModel(Base):
    """Таблица notification_dismissals — скрытые ключи inbox."""

    __tablename__ = "notification_dismissals"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "user_id",
            "notification_key",
            name="uq_notification_dismissals_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_key: Mapped[str] = mapped_column(String(120), nullable=False)
    dismissed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def to_entity(self) -> NotificationDismissalEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return NotificationDismissalEntity(
            id=self.id,
            account_id=self.account_id,
            user_id=self.user_id,
            notification_key=self.notification_key,
            dismissed_at=self.dismissed_at,
        )

    @classmethod
    def from_entity(cls, entity: NotificationDismissalEntity) -> "NotificationDismissalModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            user_id=entity.user_id,
            notification_key=entity.notification_key,
            dismissed_at=entity.dismissed_at,
        )
