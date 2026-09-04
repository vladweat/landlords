"""Сервис для построения финансового отчёта (ledger)."""

from datetime import date, datetime, timezone
from uuid import UUID
from decimal import Decimal

from app.core.exceptions import NotFoundError
from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository
from app.domain.rules import compute_ledger_lines
from app.services.dto.dashboard_dto import LedgerDTO, LedgerLineDTO
from app.services.reminder_service import ReminderService
from app.domain.interfaces import IReminderRepository

class LedgerService:
    def __init__(
        self,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        reminder_repo: IReminderRepository | None = None,
    ) -> None:
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.reminder_repo = reminder_repo

    def get_ledger(self, contract_id: UUID, account_id: UUID) -> LedgerDTO:
        """Построить полный ledger-отчёт по контракту."""
        from datetime import date, datetime, timezone

        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        charges = self.charge_repo.list_by_contract(contract_id, account_id)
        payments = self.payment_repo.list_by_contract(contract_id, account_id)

        lines = compute_ledger_lines(charges, payments)

        total_expected = sum((c.amount for c in charges), Decimal("0"))
        total_paid = sum((p.amount for p in payments), Decimal("0"))
        outstanding_balance = total_expected - total_paid

        last_payment_date = None
        if payments:
            last_payment_date = max(p.date_paid for p in payments)

        overdue_days = 0
        today = datetime.now(timezone.utc).date()
        for charge in sorted(charges, key=lambda c: c.due_date):
            paid = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
            remaining = charge.amount - paid
            if remaining > 0 and charge.due_date < today:
                overdue_days = (today - charge.due_date).days
                break

        # Обогащаем строки ledger reminder_status
        for charge in charges:
            reminder_status = None
            if self.reminder_repo:
                count = self.reminder_repo.count_by_charge(charge.id, account_id)
                reminders = self.reminder_repo.get_by_charge(charge.id, account_id)
                last_date = reminders[0].created_at.date().isoformat() if reminders else None
                can_remind = charge.status == "overdue" and (
                    count == 0 or (today - reminders[0].created_at.date()).days >= 3
                )
                next_type = "first" if count == 0 else ("second" if count == 1 else "third")
                reminder_status = {
                    "can_remind": can_remind,
                    "next_reminder_type": next_type,
                    "last_reminder_date": last_date,
                    "total_sent": count,
                }
            # Прикрепляем к соответствующей строке ledger по source_id
            for line in lines:
                if line.type == "charge" and line.source_id == charge.id:
                    line.reminder_status = reminder_status
                    break

        return LedgerDTO(
            total_expected=total_expected,
            total_paid=total_paid,
            outstanding_balance=outstanding_balance,
            lines=[LedgerLineDTO.model_validate(line) for line in lines],
            last_payment_date=last_payment_date,
            overdue_days=overdue_days,
        )