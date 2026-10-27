"""Publish PostgreSQL outbox commands to Celery with at-least-once delivery."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Event
from typing import Callable

from loguru import logger
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.repositories.outbox_message_repo import OutboxMessageRepository
from app.domain.entities import OutboxMessageEntity


@dataclass(frozen=True)
class DispatchSummary:
    claimed: int = 0
    published: int = 0
    retried: int = 0
    failed: int = 0


class OutboxRelay:
    """Claim rows in short DB transactions and publish after releasing locks."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        publisher,
        *,
        repository_factory=OutboxMessageRepository,
        batch_size: int | None = None,
        lease_seconds: int | None = None,
        max_attempts: int | None = None,
        base_backoff_seconds: float | None = None,
        max_backoff_seconds: int | None = None,
        poll_seconds: float | None = None,
        jitter_ratio: float = 0.2,
    ) -> None:
        self.session_factory = session_factory
        self.publisher = publisher
        self.repository_factory = repository_factory
        self.batch_size = batch_size or settings.OUTBOX_RELAY_BATCH_SIZE
        self.lease_seconds = lease_seconds or settings.OUTBOX_RELAY_LEASE_SECONDS
        self.max_attempts = max_attempts or settings.OUTBOX_RELAY_MAX_ATTEMPTS
        self.base_backoff_seconds = (
            base_backoff_seconds or settings.OUTBOX_RELAY_BASE_BACKOFF_SECONDS
        )
        self.max_backoff_seconds = (
            max_backoff_seconds or settings.OUTBOX_RELAY_MAX_BACKOFF_SECONDS
        )
        self.poll_seconds = poll_seconds or settings.OUTBOX_RELAY_POLL_SECONDS
        self.jitter_ratio = max(0.0, min(jitter_ratio, 0.5))

    def dispatch_once(self) -> DispatchSummary:
        claim_session = self.session_factory()
        try:
            repository = self.repository_factory(claim_session)
            messages = repository.claim_due_batch(self.batch_size, self.lease_seconds)
            claim_session.commit()
        except Exception:
            claim_session.rollback()
            raise
        finally:
            claim_session.close()

        published = retried = failed = 0
        for message in messages:
            try:
                self.publisher.send_task(
                    message.task_name,
                    args=[
                        str(message.account_id),
                        str(message.contract_id),
                        str(message.id),
                    ],
                    task_id=str(message.id),
                )
                update_session = self.session_factory()
                try:
                    self.repository_factory(update_session).mark_published(
                        message.id, message.account_id, message.lease_token
                    )
                    update_session.commit()
                except Exception:
                    update_session.rollback()
                    raise
                finally:
                    update_session.close()
                published += 1
            except Exception as exc:
                delay = self._retry_delay(message.attempts)
                update_session = self.session_factory()
                try:
                    terminal = self.repository_factory(update_session).mark_dispatch_failure(
                        message.id,
                        message.account_id,
                        message.lease_token,
                        datetime.now(timezone.utc) + timedelta(seconds=delay),
                        type(exc).__name__,
                        self.max_attempts,
                    )
                    update_session.commit()
                except Exception:
                    update_session.rollback()
                    logger.exception("outbox_failure_state_update_failed")
                    continue
                finally:
                    update_session.close()
                if terminal or message.attempts >= self.max_attempts:
                    failed += 1
                else:
                    retried += 1

        snapshot_session = self.session_factory()
        try:
            pending, oldest_age, terminal_failures = self.repository_factory(
                snapshot_session
            ).backlog_snapshot()
            snapshot_session.commit()
        except Exception:
            snapshot_session.rollback()
            logger.exception("outbox_backlog_snapshot_failed")
            pending = oldest_age = terminal_failures = 0
        finally:
            snapshot_session.close()

        summary = DispatchSummary(
            claimed=len(messages), published=published, retried=retried, failed=failed
        )
        logger.info(
            "outbox_dispatch claimed={} published={} retried={} terminal={} "
            "pending={} oldest_age_seconds={:.1f} terminal_total={}",
            summary.claimed,
            summary.published,
            summary.retried,
            summary.failed,
            pending,
            oldest_age,
            terminal_failures,
        )
        return summary

    def run(self, stop_event: Event) -> None:
        """Poll until a termination signal requests graceful shutdown."""
        while not stop_event.is_set():
            try:
                self.dispatch_once()
            except Exception:
                logger.exception("outbox_relay_iteration_failed")
            stop_event.wait(self.poll_seconds)

    def _retry_delay(self, attempts: int) -> float:
        ceiling = min(
            self.max_backoff_seconds,
            self.base_backoff_seconds * (2 ** max(0, attempts - 1)),
        )
        spread = ceiling * self.jitter_ratio
        return random.uniform(max(0.0, ceiling - spread), ceiling + spread)


def dispatch_once() -> DispatchSummary:
    """Run one dispatch iteration using application dependencies."""
    from app.celery_app import celery_app
    from app.db.session import SessionLocal

    return OutboxRelay(SessionLocal, celery_app).dispatch_once()
