"""Сервис UI-уведомлений: просрочки и окончания договоров."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.entities import NotificationDismissalEntity
from app.domain.interfaces import INotificationDismissalRepository
from app.services.calendar_service import CalendarService
from app.services.dto.notification_dto import NotificationItemDTO, NotificationListDTO


class NotificationService:
    """Вычисляемый inbox на базе календаря + dismissals."""

    ENDING_WINDOW_DAYS = 45

    def __init__(
        self,
        calendar_service: CalendarService,
        dismissal_repo: INotificationDismissalRepository,
    ) -> None:
        self.calendar_service = calendar_service
        self.dismissal_repo = dismissal_repo

    def list_notifications(
        self, account_id: UUID, user_id: UUID
    ) -> NotificationListDTO:
        """Собрать непрочитанные уведомления для пользователя."""
        today = datetime.now(timezone.utc).date()
        events = self.calendar_service.get_events(
            account_id,
            date_from=today,
            date_to=today + timedelta(days=self.ENDING_WINDOW_DAYS),
        )
        dismissed = self.dismissal_repo.list_keys(account_id, user_id)

        items: list[NotificationItemDTO] = []
        for event in events:
            if event.type == "charge_due" and event.status == "overdue" and event.charge_id:
                key = f"overdue:{event.charge_id}"
                if key in dismissed:
                    continue
                remaining = event.remaining if event.remaining is not None else Decimal("0")
                currency = event.currency or "RUB"
                address = event.property_address or "Объект"
                items.append(
                    NotificationItemDTO(
                        id=key,
                        type="charge_overdue",
                        title="Просроченная оплата",
                        body=(
                            f"{address}: остаток {remaining} {currency}"
                            + (f" ({event.tenant_name})" if event.tenant_name else "")
                        ),
                        severity="critical",
                        href=f"/contracts/{event.contract_id}",
                        created_at=event.date,
                        meta={
                            "contract_id": str(event.contract_id),
                            "charge_id": str(event.charge_id),
                            "remaining": str(remaining),
                            "currency": currency,
                        },
                    )
                )
            elif event.type == "contract_ending":
                key = f"ending:{event.contract_id}"
                if key in dismissed:
                    continue
                days = event.days_until_end if event.days_until_end is not None else 0
                address = event.property_address or "Объект"
                items.append(
                    NotificationItemDTO(
                        id=key,
                        type="contract_ending",
                        title="Окончание договора",
                        body=f"{address}: через {days} дн."
                        + (f" ({event.tenant_name})" if event.tenant_name else ""),
                        severity="warning" if days > 7 else "critical",
                        href=f"/contracts/{event.contract_id}",
                        created_at=event.date,
                        meta={
                            "contract_id": str(event.contract_id),
                            "days_until_end": days,
                            "end_date": event.date.isoformat(),
                        },
                    )
                )

        return NotificationListDTO(items=items, unread_count=len(items))

    def dismiss(
        self, account_id: UUID, user_id: UUID, notification_key: str
    ) -> None:
        """Скрыть уведомление по стабильному ключу."""
        entity = NotificationDismissalEntity(
            id=uuid4(),
            account_id=account_id,
            user_id=user_id,
            notification_key=notification_key,
            dismissed_at=datetime.now(timezone.utc),
        )
        self.dismissal_repo.dismiss(entity)
