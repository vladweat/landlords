"""Сервис аналитики и дашборда."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain.interfaces import (
    IContractRepository,
    IPaymentRepository,
    IPropertyExpenseRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import compute_occupancy_rate
from app.services.dto.dashboard_dto import DashboardSummaryDTO


class DashboardService:
    """Сервис для сбора аналитики по аккаунту."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        tenant_repo: ITenantRepository | None = None,
        expense_repo: IPropertyExpenseRepository | None = None,
    ) -> None:
        self.property_repo = property_repo
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.tenant_repo = tenant_repo
        self.expense_repo = expense_repo

    def get_summary(self, account_id: UUID) -> DashboardSummaryDTO:
        today = date.today()

        active_properties = self.property_repo.count_active(account_id)
        active_contracts = self.contract_repo.count_active(account_id)

        monthly_expected = self.charge_repo.get_total_expected_for_month(account_id, today.year, today.month)
        monthly_collected = self.payment_repo.get_total_paid_for_month(account_id, today.year, today.month)

        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1

        monthly_previous = self.payment_repo.get_monthly_income(account_id, prev_year, prev_month)

        if monthly_previous > 0:
            change_percent = round(float((monthly_collected - monthly_previous) / monthly_previous * 100), 1)
        else:
            change_percent = 0.0

        outstanding = self.charge_repo.get_total_outstanding(account_id)
        occupancy_rate = compute_occupancy_rate(active_contracts, active_properties)
        overdue_total = self.charge_repo.get_overdue_total_amount(account_id)
        overdue_count = self.charge_repo.get_overdue_count(account_id)

        # Сводка по объектам: все связи загружаются пакетно, а не внутри цикла.
        all_properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        properties = [p.to_entity() if hasattr(p, "to_entity") else p for p in all_properties.items]
        property_ids = [prop.id for prop in properties]
        active_contracts_for_properties = self.contract_repo.list_active_by_properties(
            property_ids, account_id
        )
        active_by_property = {}
        for contract in active_contracts_for_properties:
            active_by_property.setdefault(contract.property_id, contract)

        active_contract_ids = [contract.id for contract in active_by_property.values()]
        contract_ids_for_property = {
            contract.id: contract.property_id for contract in active_by_property.values()
        }
        tenant_ids = [contract.tenant_id for contract in active_by_property.values()]
        tenants_by_id = {}
        if self.tenant_repo and tenant_ids:
            tenants_by_id = {
                tenant.id: tenant
                for tenant in self.tenant_repo.list_by_ids(tenant_ids, account_id)
            }

        year_ago = today - timedelta(days=365)
        payments_by_property: dict[UUID, Decimal] = {}
        if active_contract_ids:
            payments = self.payment_repo.list_by_contracts(
                active_contract_ids, account_id, date_from=year_ago
            )
            for payment in payments:
                property_id = contract_ids_for_property.get(payment.contract_id)
                if property_id:
                    payments_by_property[property_id] = (
                        payments_by_property.get(property_id, Decimal("0")) + payment.amount
                    )

        expenses_by_property: dict[UUID, Decimal] = {}
        if self.expense_repo and property_ids:
            expenses_by_property = self.expense_repo.sum_by_property_ids(
                property_ids, account_id, start_date=year_ago, end_date=today
            )

        properties_overview = []
        for prop in properties:
            active_contract = active_by_property.get(prop.id)
            tenant = tenants_by_id.get(active_contract.tenant_id) if active_contract else None
            annual_income = payments_by_property.get(prop.id, Decimal("0"))
            income_is_forecast = False
            if active_contract and annual_income == 0:
                annual_income = active_contract.rent_amount * 12
                income_is_forecast = True

            annual_expenses = expenses_by_property.get(prop.id, Decimal("0"))
            annual_profit = annual_income - annual_expenses
            roi = None
            payback = None
            if prop.purchase_price and prop.purchase_price > 0:
                roi = round(float(annual_profit / prop.purchase_price * 100), 1)
                if annual_profit > 0:
                    payback = round(float(prop.purchase_price / annual_profit), 1)

            days_until_end = None
            if active_contract and active_contract.end_date:
                days_until_end = (active_contract.end_date - today).days

            properties_overview.append({
                "property_id": str(prop.id),
                "address": prop.get_address(),
                "tenant_name": tenant.full_name if tenant else None,
                "contract_status": active_contract.status if active_contract else None,
                "monthly_income": str(active_contract.rent_amount) if active_contract else "0",
                "roi": roi,
                "payback_years": payback,
                "annual_income": str(annual_income),
                "annual_expenses": str(annual_expenses),
                "annual_profit": str(annual_profit),
                "income_is_forecast": income_is_forecast,
                "days_until_contract_end": days_until_end,
                "has_active_contract": active_contract is not None,
            })

        return DashboardSummaryDTO(
            monthly_expected_income=monthly_expected,
            monthly_collected_income=monthly_collected,
            outstanding_balance=outstanding,
            occupancy_rate=occupancy_rate,
            active_properties=active_properties,
            active_contracts=active_contracts,
            monthly_income_previous=monthly_previous,
            monthly_income_change_percent=change_percent,
            overdue_total_amount=overdue_total,
            overdue_count=overdue_count,
            properties_overview=properties_overview,
        )

    def get_last_payments(self, account_id: UUID, limit: int = 5) -> list[dict]:
        """Последние платежи с пакетной загрузкой связанных объектов."""
        payments = self.payment_repo.list_by_account(account_id)[:limit]
        contracts = self.contract_repo.list_all_by_account(account_id)
        contract_ids = {payment.contract_id for payment in payments}
        contracts_by_id = {
            contract.id: contract for contract in contracts if contract.id in contract_ids
        }
        property_ids = list({contract.property_id for contract in contracts_by_id.values()})
        properties_by_id = {
            prop.id: prop for prop in self.property_repo.list_by_ids(property_ids, account_id)
        } if property_ids else {}
        tenant_ids = list({contract.tenant_id for contract in contracts_by_id.values()})
        tenants_by_id = {}
        if self.tenant_repo and tenant_ids:
            tenants_by_id = {
                tenant.id: tenant for tenant in self.tenant_repo.list_by_ids(tenant_ids, account_id)
            }

        data = []
        for payment in payments:
            contract = contracts_by_id.get(payment.contract_id)
            prop = properties_by_id.get(contract.property_id) if contract else None
            tenant = tenants_by_id.get(contract.tenant_id) if contract else None
            data.append({
                "id": str(payment.id),
                "contract_id": str(payment.contract_id),
                "amount": str(payment.amount),
                "date_paid": payment.date_paid.isoformat(),
                "method": payment.method,
                "property_address": prop.get_address() if prop else "",
                "tenant_name": tenant.full_name if tenant else "",
            })
        return data
