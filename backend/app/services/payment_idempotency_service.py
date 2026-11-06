"""Request idempotency для ручного POST /v1/payments."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.core.exceptions import ValidationError
from app.db.repositories.payment_idempotency_repo import PaymentIdempotencyRepository

PAYMENT_CREATE_SCOPE = "payments:create"
PAYMENT_CREATE_IDEMPOTENCY_TTL = timedelta(hours=24)
MAX_IDEMPOTENCY_KEY_LENGTH = 255


@dataclass(frozen=True)
class PaymentIdempotencyReservation:
    """Новая reservation или исходный ответ для безопасного replay."""

    record_id: UUID | None
    response_snapshot: dict[str, Any] | None

    @property
    def is_replay(self) -> bool:
        return self.response_snapshot is not None


class PaymentIdempotencyService:
    """Проверяет ключ и хеш запроса, управляет сроком хранения результата."""

    def __init__(self, repository: PaymentIdempotencyRepository) -> None:
        self.repository = repository

    def reserve_or_replay(
        self,
        *,
        account_id: UUID,
        key: str,
        request: BaseModel,
    ) -> PaymentIdempotencyReservation:
        self._validate_key(key)
        now = datetime.now(timezone.utc)
        record_id, response_snapshot = self.repository.reserve_or_replay(
            account_id=account_id,
            operation_scope=PAYMENT_CREATE_SCOPE,
            key=key,
            request_hash=self._request_hash(request),
            now=now,
            expires_at=now + PAYMENT_CREATE_IDEMPOTENCY_TTL,
        )
        return PaymentIdempotencyReservation(record_id, response_snapshot)

    def complete(
        self,
        *,
        account_id: UUID,
        record_id: UUID,
        response_snapshot: dict[str, Any],
    ) -> None:
        now = datetime.now(timezone.utc)
        self.repository.complete(
            account_id=account_id,
            operation_scope=PAYMENT_CREATE_SCOPE,
            record_id=record_id,
            response_snapshot=response_snapshot,
            expires_at=now + PAYMENT_CREATE_IDEMPOTENCY_TTL,
        )

    @staticmethod
    def _validate_key(key: str) -> None:
        if not 1 <= len(key) <= MAX_IDEMPOTENCY_KEY_LENGTH or any(
            not 0x21 <= ord(character) <= 0x7E for character in key
        ):
            raise ValidationError(
                "Idempotency-Key must contain 1 to 255 visible ASCII characters"
            )

    @staticmethod
    def _request_hash(request: BaseModel) -> str:
        canonical_request = json.dumps(
            request.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical_request.encode("utf-8")).hexdigest()
