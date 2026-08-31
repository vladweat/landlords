"""Сервис аналитики и дашборда."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain.interfaces import (
    IContractRepository,
    IPaymentRepository,
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
    ) -> None:
        self.property_repo = property_repo
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.tenant_repo = tenant_repo

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

        # Сводка по объектам
        properties_overview = []
        all_properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        for p in all_properties.items:
            prop = p.to_entity() if hasattr(p, 'to_entity') else p

            active_contract = self.contract_repo.get_active_for_property(prop.id, account_id)
            tenant_name = None
            if active_contract and self.tenant_repo:
                tenant = self.tenant_repo.get_by_id(active_contract.tenant_id, account_id)
                tenant_name = tenant.full_name if tenant else None

            annual_income = Decimal("0")
            if active_contract:
                payments = self.payment_repo.list_by_contract(active_contract.id, account_id)
                year_ago = today - timedelta(days=365)
                for payment in payments:
                    if payment.date_paid >= year_ago:
                        annual_income += payment.amount
                if annual_income == 0:
                    annual_income = active_contract.rent_amount * 12

            roi = None
            payback = None
            if prop.purchase_price and prop.purchase_price > 0 and annual_income > 0:
                roi = round(float(annual_income / prop.purchase_price * 100), 1)
                payback = round(float(prop.purchase_price / annual_income), 1)

            days_until_end = None
            if active_contract and active_contract.end_date:
                days_until_end = (active_contract.end_date - today).days

            properties_overview.append({
                "property_id": str(prop.id),
                "address": prop.get_address(),
                "tenant_name": tenant_name,
                "contract_status": active_contract.status if active_contract else None,
                "monthly_income": float(active_contract.rent_amount) if active_contract else 0,
                "roi": roi,
                "payback_years": payback,
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
            properties_overview=properties_overview,
        )

    def get_last_payments(self, account_id: UUID, limit: int = 5) -> list[dict]:
        """Последние платежи для дашборда с адресом и арендатором."""
        payments = self.payment_repo.list_by_account(account_id)[:limit]
        data = []
        for p in payments:
            contract = self.contract_repo.get_by_id(p.contract_id, account_id)
            address = ""
            tenant_name = ""
            if contract:
                prop = self.property_repo.get_by_id(contract.property_id, account_id)
                if prop:
                    address = prop.get_address()
                if self.tenant_repo:
                    tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
                    if tenant:
                        tenant_name = tenant.full_name
            data.append({
                "id": str(p.id),
                "contract_id": str(p.contract_id),
                "amount": float(p.amount),
                "date_paid": p.date_paid.isoformat(),
                "method": p.method,
                "property_address": address,
                "tenant_name": tenant_name,
            })
        return data