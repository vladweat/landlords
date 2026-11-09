"""Репозиторий request idempotency для ручных платежей."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.db.models.payment_idempotency_model import PaymentIdempotencyRecordModel


class PaymentIdempotencyRepository:
    """Резервирует account-scoped ключи и хранит завершённый JSON-ответ."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def reserve_or_replay(
        self,
        *,
        account_id: UUID,
        operation_scope: str,
        key: str,
        request_hash: str,
        now: datetime,
        expires_at: datetime,
    ) -> tuple[UUID | None, dict[str, Any] | None]:
        """Создать незавершённую reservation или вернуть сохранённый ответ."""
        while True:
            self.delete_expired_for_account(
                account_id=account_id,
                operation_scope=operation_scope,
                now=now,
            )

            record_id = uuid4()
            result = self.session.execute(
                insert(PaymentIdempotencyRecordModel)
                .values(
                    id=record_id,
                    account_id=account_id,
                    operation_scope=operation_scope,
                    key=key,
                    request_hash=request_hash,
                    status="in_progress",
                    response_snapshot=None,
                    expires_at=expires_at,
                )
                .on_conflict_do_nothing(constraint="uq_payment_idempotency_scope_key")
            )
            if result.rowcount == 1:
                return record_id, None

            existing = (
                self.session.query(PaymentIdempotencyRecordModel)
                .filter_by(
                    account_id=account_id,
                    operation_scope=operation_scope,
                    key=key,
                )
                .with_for_update()
                .one_or_none()
            )
            if existing is None:
                # A concurrently expired row may have been deleted after the
                # conflicting insert. Retry reservation in this transaction.
                continue
            if existing.expires_at <= now:
                self.session.delete(existing)
                self.session.flush()
                continue
            if existing.request_hash != request_hash:
                raise ConflictError(
                    "Idempotency-Key was already used with a different request"
                )
            if existing.status == "completed" and existing.response_snapshot is not None:
                return None, existing.response_snapshot

            # In-progress rows normally remain uncommitted with their payment
            # transaction. This handles any stale committed row until its TTL.
            raise ConflictError("A request with this Idempotency-Key is in progress")

    def delete_expired_for_account(
        self,
        *,
        account_id: UUID,
        operation_scope: str,
        now: datetime,
        limit: int | None = None,
    ) -> int:
        """Delete expired records visible in one tenant, optionally in a batch."""
        filters = (
            PaymentIdempotencyRecordModel.account_id == account_id,
            PaymentIdempotencyRecordModel.operation_scope == operation_scope,
            PaymentIdempotencyRecordModel.expires_at <= now,
        )
        if limit is None:
            result = self.session.execute(
                delete(PaymentIdempotencyRecordModel).where(*filters)
            )
            self.session.flush()
            return result.rowcount or 0

        expired_ids = (
            select(PaymentIdempotencyRecordModel.id)
            .where(*filters)
            .order_by(
                PaymentIdempotencyRecordModel.expires_at,
                PaymentIdempotencyRecordModel.id,
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
            .cte("expired_payment_idempotency_records")
        )
        result = self.session.execute(
            delete(PaymentIdempotencyRecordModel).where(
                PaymentIdempotencyRecordModel.id.in_(select(expired_ids.c.id))
            )
        )
        self.session.flush()
        return result.rowcount or 0

    def complete(
        self,
        *,
        account_id: UUID,
        operation_scope: str,
        record_id: UUID,
        response_snapshot: dict[str, Any],
        expires_at: datetime,
    ) -> None:
        """Сохранить ответ в той же транзакции, что и бизнес-изменения."""
        record = (
            self.session.query(PaymentIdempotencyRecordModel)
            .filter_by(
                id=record_id,
                account_id=account_id,
                operation_scope=operation_scope,
            )
            .with_for_update()
            .one()
        )
        record.status = "completed"
        record.response_snapshot = response_snapshot
        record.expires_at = expires_at
        self.session.flush()
