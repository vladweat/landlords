"""Неизменяемый снимок начисления для разрешения ссылок allocation history."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Date,
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


class PaymentAllocationTargetModel(Base):
    """Стабильная tenant-scoped ссылка и снимок начисления."""

    __tablename__ = "payment_allocation_targets"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "contract_id",
            "id",
            name="uq_payment_allocation_targets_tenant_contract_id",
        ),
        ForeignKeyConstraint(
            ["account_id", "contract_id"],
            ["contracts.account_id", "contracts.id"],
            name="fk_payment_allocation_targets_tenant_contract",
            ondelete="NO ACTION",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    original_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
