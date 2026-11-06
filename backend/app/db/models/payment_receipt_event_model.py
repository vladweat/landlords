"""Append-only журнал исправлений и отмен receipt."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import PaymentReceiptEventEntity


class PaymentReceiptEventModel(Base):
    """Корректировка суммы или отмена строки проекции платежа."""

    __tablename__ = "payment_receipt_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('correction', 'cancellation')",
            name="ck_payment_receipt_events_type",
        ),
        CheckConstraint(
            "event_type <> 'cancellation' OR amount_delta < 0",
            name="ck_payment_receipt_events_cancellation_negative",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id"],
            [
                "payment_receipts.account_id",
                "payment_receipts.contract_id",
                "payment_receipts.id",
            ],
            name="fk_payment_receipt_events_receipt",
            ondelete="CASCADE",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    receipt_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    resulting_date_paid: Mapped[date] = mapped_column(Date, nullable=False)
    resulting_method: Mapped[str] = mapped_column(String(20), nullable=False)
    resulting_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def from_entity(cls, entity: PaymentReceiptEventEntity) -> "PaymentReceiptEventModel":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            receipt_id=entity.receipt_id,
            event_type=entity.event_type,
            amount_delta=entity.amount_delta,
            resulting_date_paid=entity.resulting_date_paid,
            resulting_method=entity.resulting_method,
            resulting_note=entity.resulting_note,
            created_at=entity.created_at,
        )
