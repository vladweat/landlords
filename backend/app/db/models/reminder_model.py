"""ORM-модель напоминания."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import ReminderEntity


class ReminderModel(TimestampMixin, Base):
    """Таблица reminders."""

    __tablename__ = "reminders"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    charge_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rent_charges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reminder_type: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_entity(self) -> ReminderEntity:
        return ReminderEntity(
            id=self.id, account_id=self.account_id, contract_id=self.contract_id,
            charge_id=self.charge_id, reminder_type=self.reminder_type,
            message_text=self.message_text, created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: ReminderEntity) -> "ReminderModel":
        return cls(
            id=entity.id, account_id=entity.account_id, contract_id=entity.contract_id,
            charge_id=entity.charge_id, reminder_type=entity.reminder_type,
            message_text=entity.message_text, created_at=entity.created_at,
        )