"""Сервис напоминаний о просрочке."""

from datetime import date, timedelta
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ReminderEntity
from app.domain.interfaces import (
    IContractEventRepository,
    IContractRepository,
    IInvoiceRepository,
    IRentChargeRepository,
    IReminderRepository,
    ITenantRepository,
)
from app.services.dto.reminder_dto import ReminderDTO, ReminderCreateDTO
from app.domain.entities import ContractEventEntity
from app.services.contract_event_labels import reminder_type_label


class ReminderService:
    TEMPLATES = {
        "first": (
            "{tenant_name}, добрый день! Напоминаю об оплате аренды за {period} "
            "по договору от {start_date}. Сумма к оплате: {amount} ₽. "
            "Буду благодарен за перевод до {deadline}. Спасибо!"
        ),
        "second": (
            "{tenant_name}, здравствуйте. К сожалению, оплата за {period} "
            "в размере {amount} ₽ до сих пор не поступила. Просрочка составляет {overdue_days} дней. "
            "Прошу оплатить задолженность в ближайшие 3 дня во избежание штрафных санкций по договору."
        ),
        "third": (
            "{tenant_name}, это третье уведомление о задолженности по арендной плате. "
            "Сумма долга: {amount} ₽, просрочка: {overdue_days} дней. "
            "Прошу срочно связаться со мной для урегулирования ситуации."
        ),
    }

    def __init__(
        self,
        reminder_repo: IReminderRepository,
        charge_repo: IRentChargeRepository,
        contract_repo: IContractRepository,
        tenant_repo: ITenantRepository,
        event_repo: IContractEventRepository | None = None,
        invoice_repo: IInvoiceRepository | None = None,
    ) -> None:
        self.reminder_repo = reminder_repo
        self.charge_repo = charge_repo
        self.contract_repo = contract_repo
        self.tenant_repo = tenant_repo
        self.event_repo = event_repo
        self.invoice_repo = invoice_repo

    def _invoice_share_url(self, charge_id: UUID, account_id: UUID) -> str | None:
        if not self.invoice_repo:
            return None
        invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice:
            return None
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/i/{invoice.public_token}"

    def generate_message(self, charge_id: UUID, account_id: UUID, reminder_type: str) -> str:
        charge = self.charge_repo.get_by_id(charge_id, account_id)
        if not charge:
            raise NotFoundError(f"Charge {charge_id} not found")
        contract = self.contract_repo.get_by_id(charge.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {charge.contract_id} not found")
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        template = self.TEMPLATES.get(reminder_type, self.TEMPLATES["first"])
        today = date.today()
        overdue_days = (today - charge.due_date).days if charge.due_date < today else 0

        message = template.format(
            tenant_name=tenant.full_name,
            period=f"{charge.period_start} — {charge.period_end}",
            start_date=contract.start_date.strftime("%d.%m.%Y"),
            amount=charge.amount,
            overdue_days=overdue_days,
            deadline=(today + timedelta(days=3)).strftime("%d.%m.%Y"),
        )
        share_url = self._invoice_share_url(charge_id, account_id)
        if share_url:
            message = f"{message}\n\nКвитанция: {share_url}"
        return message

    def create_reminder(self, account_id: UUID, dto: ReminderCreateDTO) -> ReminderDTO:
        charge = self.charge_repo.get_by_id(dto.charge_id, account_id)
        if not charge:
            raise NotFoundError(f"Charge {dto.charge_id} not found")
        if charge.status != "overdue":
            raise ValidationError("Reminder can only be sent for overdue charges")

        count = self.reminder_repo.count_by_charge(dto.charge_id, account_id)
        if count >= 3:
            raise ValidationError("Maximum 3 reminders per charge")

        message = self.generate_message(dto.charge_id, account_id, dto.reminder_type)
        entity = ReminderEntity(
            id=uuid4(), account_id=account_id, contract_id=charge.contract_id,
            charge_id=dto.charge_id, reminder_type=dto.reminder_type, message_text=message,
        )
        created = self.reminder_repo.create(entity)

        if self.event_repo:
            self.event_repo.create(ContractEventEntity(
                id=uuid4(), account_id=account_id, contract_id=entity.contract_id,
                event_type="reminder",
                title=f"Напоминание о просрочке ({reminder_type_label(entity.reminder_type)})",
                description=message,
                event_metadata={"reminder_id": str(created.id)},
            ))

        return ReminderDTO.model_validate(created)

    def get_reminders(self, charge_id: UUID, account_id: UUID) -> list[ReminderDTO]:
        entities = self.reminder_repo.get_by_charge(charge_id, account_id)
        return [ReminderDTO.model_validate(e) for e in entities]

    def should_show_reminder(self, charge_id: UUID, account_id: UUID) -> dict:
        charge = self.charge_repo.get_by_id(charge_id, account_id)
        if not charge or charge.status != "overdue":
            return {"can_remind": False}

        count = self.reminder_repo.count_by_charge(charge_id, account_id)
        if count == 0:
            return {"can_remind": True, "reminder_type": "first", "reminder_count": 0}
        elif count == 1:
            last = self.reminder_repo.get_by_charge(charge_id, account_id)[0]
            days_since = (date.today() - last.created_at.date()).days
            if days_since >= 3:
                return {"can_remind": True, "reminder_type": "second", "reminder_count": 1}
        elif count == 2:
            last = self.reminder_repo.get_by_charge(charge_id, account_id)[0]
            days_since = (date.today() - last.created_at.date()).days
            if days_since >= 3:
                return {"can_remind": True, "reminder_type": "third", "reminder_count": 2}

        return {"can_remind": False, "reminder_count": count}
