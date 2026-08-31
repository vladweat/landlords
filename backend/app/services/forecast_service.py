"""Сервис прогноза дохода."""

from collections import defaultdict
from datetime import date
from decimal import Decimal
from uuid import UUID

from app.domain.interfaces import IContractRepository, IPropertyRepository, IRentChargeRepository


class ForecastService:
    """Сервис прогнозирования дохода."""

    def __init__(
        self,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        property_repo: IPropertyRepository | None = None,
    ) -> None:
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.property_repo = property_repo

    def get_forecast(self, account_id: UUID) -> dict:
        """Прогноз дохода до конца года."""
        today = date.today()
        year_end = date(today.year, 12, 31)

        contracts = self.contract_repo.list_by_account(account_id)
        active_contracts = [
            c for c in contracts.items
            if c.status in ("active", "overdue") and c.end_date >= today
        ]

        monthly: dict[str, Decimal] = defaultdict(Decimal)
        ending_alerts: list[dict] = []

        for contract in active_contracts:
            charges = self.charge_repo.list_by_contract(contract.id, account_id)
            for charge in charges:
                if charge.due_date >= today and charge.due_date <= year_end:
                    month_key = charge.due_date.strftime("%Y-%m")
                    monthly[month_key] += charge.amount

            days_left = (contract.end_date - today).days
            if days_left <= 60:
                address = "..."
                if self.property_repo:
                    prop = self.property_repo.get_by_id(contract.property_id, account_id)
                    if prop:
                        address = prop.get_address()
                ending_alerts.append({
                    "type": "contract_ending",
                    "contract_id": str(contract.id),
                    "property_address": address,
                    "end_date": contract.end_date.isoformat(),
                    "monthly_income": float(contract.rent_amount),
                    "days_until_end": days_left,
                })

        sorted_months = sorted(monthly.items())
        monthly_breakdown = [
            {
                "month": month,
                "expected_income": float(amount),
                "contracts_ending": len([
                    c for c in active_contracts
                    if c.end_date.strftime("%Y-%m") == month
                ]),
            }
            for month, amount in sorted_months
        ]

        total = sum(float(a) for _, a in sorted_months)

        return {
            "total_to_year_end": total,
            "monthly_breakdown": monthly_breakdown,
            "alerts": ending_alerts,
        }