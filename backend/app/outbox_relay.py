"""Foreground process entry point for the transactional outbox relay."""

import signal
from threading import Event

from loguru import logger

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.services.outbox_relay import OutboxRelay


def main() -> None:
    stop_event = Event()

    def request_stop(signum, _frame) -> None:
        logger.info("outbox_relay_shutdown_requested signal={}", signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    OutboxRelay(
        SessionLocal,
        celery_app,
        poll_seconds=settings.OUTBOX_RELAY_POLL_SECONDS,
    ).run(stop_event)


if __name__ == "__main__":
    main()
