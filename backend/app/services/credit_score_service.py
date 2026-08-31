"""Сервис расчёта кредитного рейтинга арендатора."""

from datetime import date
from uuid import UUID

from app.domain.interfaces import IPaymentRepository, IRentChargeRepository


class CreditScoreService:
    def __init__(self, payment_repo: IPaymentRepository, charge_repo: IRentChargeRepository) -> None:
        self.payment_repo = payment_repo
        self.charge_repo = charge_repo

    def calculate(self, tenant_id: UUID, account_id: UUID) -> dict:
        payments = self.payment_repo.get_by_tenant(tenant_id, account_id)

        if len(payments) < 3:
            return self._no_data(tenant_id)

        total = len(payments)
        on_time = 0
        late = 0
        total_delay = 0
        severe_late = 0

        for payment in payments:
            if payment.rent_charge_id:
                charge = self.charge_repo.get_by_id(payment.rent_charge_id, account_id)
                if charge:
                    delay = (payment.date_paid - charge.due_date).days
                    if delay <= 0:
                        on_time += 1
                    else:
                        late += 1
                        total_delay += delay
                        if delay > 30:
                            severe_late += 1
                else:
                    on_time += 1
            else:
                on_time += 1

        on_time_percent = round(on_time / total * 100, 1) if total > 0 else 0
        avg_delay = round(total_delay / late, 1) if late > 0 else 0

        if on_time_percent >= 90 and avg_delay <= 5 and severe_late == 0:
            score = "reliable"
        elif on_time_percent >= 70 and avg_delay <= 14 and severe_late <= 1:
            score = "average"
        else:
            score = "problematic"

        return {
            "tenant_id": str(tenant_id),
            "score": score,
            "metrics": {
                "total_payments": total,
                "on_time_payments": on_time,
                "on_time_percent": on_time_percent,
                "late_payments": late,
                "avg_delay_days": avg_delay,
                "severe_late_count": severe_late,
            },
            "updated_at": date.today().isoformat(),
        }

    def _no_data(self, tenant_id: UUID) -> dict:
        return {
            "tenant_id": str(tenant_id),
            "score": "no_data",
            "metrics": {
                "total_payments": 0, "on_time_payments": 0,
                "on_time_percent": 0.0, "late_payments": 0,
                "avg_delay_days": 0, "severe_late_count": 0,
            },
            "updated_at": date.today().isoformat(),
        }