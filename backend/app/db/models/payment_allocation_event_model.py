"""Append-only журнал распределений и их компенсаций."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import PaymentAllocationEventEntity


class PaymentAllocationEventModel(Base):
    """Положительная allocation или signed reversal предыдущей allocation."""

    __tablename__ = "payment_allocation_events"
    __table_args__ = (
        CheckConstraint(
            "(event_type = 'allocation' AND amount > 0 AND reverses_event_id IS NULL) OR "
            "(event_type = 'reversal' AND amount < 0 AND reverses_event_id IS NOT NULL)",
            name="ck_payment_allocation_events_shape",
        ),
        UniqueConstraint(
            "account_id",
            "contract_id",
            "receipt_id",
            "id",
            name="uq_payment_allocation_events_receipt_id",
        ),
        UniqueConstraint(
            "account_id",
            "contract_id",
            "receipt_id",
            "reverses_event_id",
            name="uq_payment_allocation_events_single_reversal",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id"],
            [
                "payment_receipts.account_id",
                "payment_receipts.contract_id",
                "payment_receipts.id",
            ],
            name="fk_payment_allocation_events_receipt",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id", "rent_charge_id"],
            [
                "payment_allocation_targets.account_id",
                "payment_allocation_targets.contract_id",
                "payment_allocation_targets.id",
            ],
            name="fk_payment_allocation_events_charge_target",
            ondelete="NO ACTION",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id", "reverses_event_id"],
            [
                "payment_allocation_events.account_id",
                "payment_allocation_events.contract_id",
                "payment_allocation_events.receipt_id",
                "payment_allocation_events.id",
            ],
            name="fk_payment_allocation_events_reversal_target",
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
    rent_charge_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reverses_event_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def from_entity(
        cls, entity: PaymentAllocationEventEntity
    ) -> "PaymentAllocationEventModel":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            receipt_id=entity.receipt_id,
            rent_charge_id=entity.rent_charge_id,
            event_type=entity.event_type,
            amount=entity.amount,
            reverses_event_id=entity.reverses_event_id,
            created_at=entity.created_at,
        )
