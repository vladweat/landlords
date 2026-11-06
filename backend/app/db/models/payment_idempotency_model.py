"""ORM-модель ключей идемпотентности ручного создания платежей."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base


class PaymentIdempotencyRecordModel(Base):
    """Сохранённая reservation и JSON-ответ для повторного POST платежа."""

    __tablename__ = "payment_idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "operation_scope",
            "key",
            name="uq_payment_idempotency_scope_key",
        ),
        CheckConstraint(
            "status IN ('in_progress', 'completed')",
            name="ck_payment_idempotency_status",
        ),
        CheckConstraint(
            "(status = 'in_progress' AND response_snapshot IS NULL) OR "
            "(status = 'completed' AND response_snapshot IS NOT NULL)",
            name="ck_payment_idempotency_response_state",
        ),
        Index(
            "ix_payment_idempotency_expiration",
            "account_id",
            "operation_scope",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    operation_scope: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    response_snapshot: Mapped[dict | None] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
