"""ORM-модель события контракта."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import ContractEventEntity


class ContractEventModel(TimestampMixin, Base):
    """Таблица contract_events."""

    __tablename__ = "contract_events"

    __table_args__ = (
        ForeignKeyConstraint(
            ["account_id", "contract_id", "payment_receipt_id"],
            [
                "payment_receipts.account_id",
                "payment_receipts.contract_id",
                "payment_receipts.id",
            ],
            name="fk_contract_events_payment_receipt",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    payment_receipt_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True, index=True
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def to_entity(self) -> ContractEventEntity:
        return ContractEventEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            event_type=self.event_type,
            title=self.title,
            description=self.description,
            event_metadata=self.event_metadata,
            created_by=self.created_by,
            created_at=self.created_at,
            payment_receipt_id=self.payment_receipt_id,
        )
    
    @classmethod
    def from_entity(cls, entity: ContractEventEntity) -> "ContractEventModel":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            event_type=entity.event_type,
            title=entity.title,
            description=entity.description,
            event_metadata=entity.event_metadata,
            created_by=entity.created_by,
            created_at=entity.created_at,
            payment_receipt_id=entity.payment_receipt_id,
        )
