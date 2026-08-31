"""ORM-модель обратной связи."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import FeedbackEntity


class FeedbackModel(TimestampMixin, Base):
    """Таблица feedback."""

    __tablename__ = "feedback"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def to_entity(self) -> FeedbackEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return FeedbackEntity(
            id=self.id,
            account_id=self.account_id,
            user_id=self.user_id,
            category=self.category,
            message=self.message,
            status=self.status,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: FeedbackEntity) -> "FeedbackModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            user_id=entity.user_id,
            category=entity.category,
            message=entity.message,
            status=entity.status,
            created_at=entity.created_at,
        )