"""Неизменяемый факт получения денег."""

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
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import PaymentReceiptEntity


class PaymentReceiptModel(Base):
    """Исходное поступление, не изменяемое после создания."""

    __tablename__ = "payment_receipts"
    __table_args__ = (
        CheckConstraint("original_amount > 0", name="ck_payment_receipts_amount_positive"),
        CheckConstraint(
            "source IN ('manual', 'tenant_claim')",
            name="ck_payment_receipts_source",
        ),
        UniqueConstraint(
            "account_id",
            "contract_id",
            "id",
            name="uq_payment_receipts_tenant_contract_id",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id"],
            ["contracts.account_id", "contracts.id"],
            name="fk_payment_receipts_tenant_contract",
            ondelete="NO ACTION",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    date_paid: Mapped[date] = mapped_column(Date, nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    method: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    @classmethod
    def from_entity(cls, entity: PaymentReceiptEntity) -> "PaymentReceiptModel":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            date_paid=entity.date_paid,
            original_amount=entity.original_amount,
            currency=entity.currency,
            method=entity.method,
            source=entity.source,
            note=entity.note,
            created_at=entity.created_at,
        )
