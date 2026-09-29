"""Рассылка писем владельцу о просрочках и окончании договоров."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.core.config import settings
from app.domain.entities import EmailDispatchLogEntity
from app.domain.interfaces import (
    IAccountRepository,
    IEmailDispatchLogRepository,
    IUserRepository,
)
from app.services.calendar_service import CalendarService
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from loguru import logger


class ReminderEmailService:
    """Ежедневная рассылка landlord-уведомлений на email owner."""

    DEDUP_DAYS = 7
    ENDING_WINDOW_DAYS = NotificationService.ENDING_WINDOW_DAYS

    def __init__(
        self,
        account_repo: IAccountRepository,
        user_repo: IUserRepository,
        calendar_service: CalendarService,
        dispatch_log_repo: IEmailDispatchLogRepository,
        email_service: EmailService | None = None,
    ) -> None:
        self.account_repo = account_repo
        self.user_repo = user_repo
        self.calendar_service = calendar_service
        self.dispatch_log_repo = dispatch_log_repo
        self.email_service = email_service or EmailService()

    def send_daily_reminders(self) -> dict[str, int]:
        """Обойти аккаунты и отправить письма owner при необходимости."""
        frontend = settings.FRONTEND_URL.rstrip("/")
        today = datetime.now(timezone.utc).date()
        sent = 0
        skipped = 0
        errors = 0

        for account in self.account_repo.list_all():
            owner = self.user_repo.get_by_id(account.owner_id)
            if not owner or not owner.is_active or not owner.email:
                continue

            events = self.calendar_service.get_events(
                account.id,
                date_from=today,
                date_to=today + timedelta(days=self.ENDING_WINDOW_DAYS),
            )

            for event in events:
                if event.type == "charge_due" and event.status == "overdue" and event.charge_id:
                    key = f"overdue:{event.charge_id}"
                    if self.dispatch_log_repo.was_sent_recently(
                        account.id, key, self.DEDUP_DAYS
                    ):
                        skipped += 1
                        continue
                    remaining = event.remaining if event.remaining is not None else Decimal("0")
                    currency = event.currency or "RUB"
                    address = event.property_address or "Объект"
                    href = f"{frontend}/contracts/{event.contract_id}"
                    try:
                        self.email_service.send_charge_overdue(
                            to=owner.email,
                            property_address=address,
                            remaining=str(remaining),
                            currency=currency,
                            tenant_name=event.tenant_name,
                            contract_href=href,
                        )
                        self.dispatch_log_repo.record(
                            EmailDispatchLogEntity(
                                id=uuid4(),
                                account_id=account.id,
                                notification_key=key,
                            )
                        )
                        sent += 1
                    except Exception:
                        logger.exception(
                            "Failed overdue email account_id={} key={}",
                            account.id,
                            key,
                        )
                        errors += 1

                elif event.type == "contract_ending":
                    key = f"ending:{event.contract_id}"
                    if self.dispatch_log_repo.was_sent_recently(
                        account.id, key, self.DEDUP_DAYS
                    ):
                        skipped += 1
                        continue
                    days = event.days_until_end if event.days_until_end is not None else 0
                    address = event.property_address or "Объект"
                    href = f"{frontend}/contracts/{event.contract_id}"
                    try:
                        self.email_service.send_contract_ending(
                            to=owner.email,
                            property_address=address,
                            days_until_end=days,
                            tenant_name=event.tenant_name,
                            contract_href=href,
                        )
                        self.dispatch_log_repo.record(
                            EmailDispatchLogEntity(
                                id=uuid4(),
                                account_id=account.id,
                                notification_key=key,
                            )
                        )
                        sent += 1
                    except Exception:
                        logger.exception(
                            "Failed ending email account_id={} key={}",
                            account.id,
                            key,
                        )
                        errors += 1

        return {"sent": sent, "skipped": skipped, "errors": errors}
