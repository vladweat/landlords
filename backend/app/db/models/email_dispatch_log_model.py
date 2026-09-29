"""ORM-модель лога отправленных email-уведомлений."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import EmailDispatchLogEntity


class EmailDispatchLogModel(Base):
    """Таблица email_dispatch_log — дедуп писем о просрочке/конце договора."""

    __tablename__ = "email_dispatch_log"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "notification_key",
            name="uq_email_dispatch_log_key",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notification_key: Mapped[str] = mapped_column(String(120), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def to_entity(self) -> EmailDispatchLogEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return EmailDispatchLogEntity(
            id=self.id,
            account_id=self.account_id,
            notification_key=self.notification_key,
            sent_at=self.sent_at,
        )

    @classmethod
    def from_entity(cls, entity: EmailDispatchLogEntity) -> "EmailDispatchLogModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            notification_key=entity.notification_key,
            sent_at=entity.sent_at,
        )
