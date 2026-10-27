"""SQLAlchemy repository for durable background commands."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.outbox_message_model import OutboxMessageModel
from app.domain.entities import OutboxMessageEntity
from app.domain.interfaces import IOutboxMessageRepository

CHARGE_GENERATION_TASK = "app.tasks.charge_tasks.generate_charges_for_contract"


class OutboxMessageRepository(IOutboxMessageRepository):
    """Persist and lease allow-listed task messages without committing."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_charge_generation(self, account_id: UUID, contract_id: UUID) -> UUID:
        task_id = uuid4()
        self.session.add(
            OutboxMessageModel(
                id=task_id,
                account_id=account_id,
                contract_id=contract_id,
                task_name=CHARGE_GENERATION_TASK,
                payload_version=1,
                status="pending",
                attempts=0,
                task_failures=0,
            )
        )
        self.session.flush()
        return task_id

    def claim_due_batch(
        self, batch_size: int, lease_seconds: int
    ) -> list[OutboxMessageEntity]:
        now = datetime.now(timezone.utc)
        rows = self.session.scalars(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.status.in_(("pending", "published")),
                OutboxMessageModel.available_at <= now,
                or_(
                    OutboxMessageModel.lease_until.is_(None),
                    OutboxMessageModel.lease_until <= now,
                ),
            )
            .order_by(OutboxMessageModel.created_at, OutboxMessageModel.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        ).all()
        for row in rows:
            row.status = "leased"
            row.lease_until = now + timedelta(seconds=lease_seconds)
            row.lease_token = uuid4()
            row.attempts += 1
        self.session.flush()
        return [row.to_entity() for row in rows]

    def get_for_update(
        self, outbox_id: UUID, account_id: UUID
    ) -> OutboxMessageEntity | None:
        row = self.session.scalar(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.id == outbox_id,
                OutboxMessageModel.account_id == account_id,
            )
            .with_for_update()
        )
        return row.to_entity() if row else None

    def mark_published(
        self, outbox_id: UUID, account_id: UUID, lease_token: UUID
    ) -> bool:
        row = self.session.scalar(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.id == outbox_id,
                OutboxMessageModel.account_id == account_id,
                OutboxMessageModel.status == "leased",
                OutboxMessageModel.lease_token == lease_token,
            )
            .with_for_update()
        )
        if row is None:
            return False
        row.status = "published"
        row.published_at = datetime.now(timezone.utc)
        row.available_at = row.lease_until or datetime.now(timezone.utc)
        row.lease_until = None
        row.lease_token = None
        self.session.flush()
        return True

    def mark_dispatch_failure(
        self,
        outbox_id: UUID,
        account_id: UUID,
        lease_token: UUID,
        available_at: datetime,
        error_type: str,
        max_attempts: int,
    ) -> bool:
        row = self.session.scalar(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.id == outbox_id,
                OutboxMessageModel.account_id == account_id,
                OutboxMessageModel.status == "leased",
                OutboxMessageModel.lease_token == lease_token,
            )
            .with_for_update()
        )
        if row is None:
            return False
        row.last_error = error_type[:80]
        row.lease_until = None
        row.lease_token = None
        row.available_at = available_at
        row.status = "pending" if row.attempts < max_attempts else "failed"
        if row.status == "failed":
            row.failed_at = datetime.now(timezone.utc)
        self.session.flush()
        return True

    def mark_completed(self, outbox_id: UUID, account_id: UUID) -> None:
        row = self.session.scalar(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.id == outbox_id,
                OutboxMessageModel.account_id == account_id,
            )
            .with_for_update()
        )
        if row is None:
            raise LookupError("Outbox message does not exist")
        if row.status == "completed":
            return
        if row.status == "failed":
            raise RuntimeError("Terminal outbox message cannot be completed")
        row.status = "completed"
        row.completed_at = datetime.now(timezone.utc)
        row.lease_until = None
        row.lease_token = None
        row.last_error = None
        self.session.flush()

    def record_task_failure(
        self,
        outbox_id: UUID,
        account_id: UUID,
        error_type: str,
        max_failures: int,
        available_at: datetime,
    ) -> bool:
        row = self.session.scalar(
            select(OutboxMessageModel)
            .where(
                OutboxMessageModel.id == outbox_id,
                OutboxMessageModel.account_id == account_id,
            )
            .with_for_update()
        )
        if row is None or row.status in ("completed", "failed"):
            return False
        row.task_failures += 1
        row.last_error = error_type[:80]
        row.lease_until = None
        row.lease_token = None
        row.available_at = available_at
        row.status = "failed" if row.task_failures >= max_failures else "published"
        if row.status == "failed":
            row.failed_at = datetime.now(timezone.utc)
        self.session.flush()
        return row.status == "failed"

    def backlog_snapshot(self) -> tuple[int, float, int]:
        now = datetime.now(timezone.utc)
        pending_count, oldest_created_at = self.session.execute(
            select(
                func.count(OutboxMessageModel.id),
                func.min(OutboxMessageModel.created_at),
            ).where(OutboxMessageModel.status.in_(("pending", "leased", "published")))
        ).one()
        terminal_failures = self.session.scalar(
            select(func.count(OutboxMessageModel.id)).where(
                OutboxMessageModel.status == "failed"
            )
        )
        age_seconds = (
            max(0.0, (now - oldest_created_at).total_seconds())
            if oldest_created_at
            else 0.0
        )
        return pending_count, age_seconds, terminal_failures or 0
