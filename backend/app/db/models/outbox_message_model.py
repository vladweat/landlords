"""ORM-модель transactional outbox для генерации начислений."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import OutboxMessageEntity


class OutboxMessageModel(Base):
    """Долговечная команда Celery, связанная с account и contract."""

    __tablename__ = "task_outbox"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'leased', 'published', 'completed', 'failed')",
            name="ck_task_outbox_status",
        ),
        CheckConstraint("attempts >= 0", name="ck_task_outbox_attempts_nonnegative"),
        CheckConstraint(
            "task_failures >= 0", name="ck_task_outbox_task_failures_nonnegative"
        ),
        Index(
            "ix_task_outbox_dispatchable",
            "status",
            "available_at",
            "lease_until",
            "created_at",
        ),
        Index("ix_task_outbox_account_contract", "account_id", "contract_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_name: Mapped[str] = mapped_column(String(160), nullable=False)
    payload_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    task_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_token: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(80))

    def to_entity(self) -> OutboxMessageEntity:
        return OutboxMessageEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            task_name=self.task_name,
            payload_version=self.payload_version,
            status=self.status,
            attempts=self.attempts,
            task_failures=self.task_failures,
            created_at=self.created_at,
            available_at=self.available_at,
            lease_until=self.lease_until,
            lease_token=self.lease_token,
            published_at=self.published_at,
            completed_at=self.completed_at,
            failed_at=self.failed_at,
            last_error=self.last_error,
        )
