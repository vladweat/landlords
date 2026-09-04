"""Сервис расчёта доходности объектов."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain.interfaces import (
    IContractRepository,
    IPaymentRepository,
    IPropertyExpenseRepository,
    IPropertyRepository,
)


class RoiService:
    """Сервис расчёта ROI для объектов недвижимости."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        contract_repo: IContractRepository,
        payment_repo: IPaymentRepository,
        expense_repo: IPropertyExpenseRepository,
    ) -> None:
        self.property_repo = property_repo
        self.contract_repo = contract_repo
        self.payment_repo = payment_repo
        self.expense_repo = expense_repo

    def calculate_annual_income(
        self, property_id: UUID, account_id: UUID
    ) -> tuple[Decimal, bool]:
        """Годовой доход: реальные платежи за 12 месяцев по всем контрактам объекта.

        Returns:
            (amount, income_is_forecast) — forecast=True если подставлен rent×12.
        """
        today = date.today()
        year_ago = today - timedelta(days=365)

        total = Decimal("0")

        all_contracts = self.contract_repo.list_all_by_account(account_id)
        for contract in all_contracts:
            if contract.property_id == property_id:
                payments = self.payment_repo.list_by_contract(contract.id, account_id)
                for p in payments:
                    if p.date_paid >= year_ago:
                        total += p.amount

        if total == Decimal("0"):
            active = self.contract_repo.get_active_for_property(property_id, account_id)
            if active:
                return active.rent_amount * 12, True

        return total, False

    def calculate_annual_expenses(self, property_id: UUID, account_id: UUID) -> Decimal:
        """Годовые расходы по объекту за последние 12 месяцев."""
        today = date.today()
        year_ago = today - timedelta(days=365)
        return self.expense_repo.get_total_for_property(
            property_id, account_id, start_date=year_ago, end_date=today
        )

    def _roi_payload(
        self,
        annual_income: Decimal,
        annual_expenses: Decimal,
        purchase_price: Decimal | None,
        income_is_forecast: bool = False,
    ) -> dict:
        """Собрать ответ ROI: прибыль = доход − расход."""
        annual_profit = annual_income - annual_expenses
        if not purchase_price or purchase_price == 0:
            return {
                "annual_income": annual_income,
                "annual_expenses": annual_expenses,
                "annual_profit": annual_profit,
                "roi": None,
                "payback_years": None,
                "income_is_forecast": income_is_forecast,
            }

        roi = round(float(annual_profit / purchase_price * 100), 1)
        payback = (
            round(float(purchase_price / annual_profit), 1)
            if annual_profit > 0
            else None
        )
        return {
            "annual_income": annual_income,
            "annual_expenses": annual_expenses,
            "annual_profit": annual_profit,
            "roi": roi,
            "payback_years": payback,
            "income_is_forecast": income_is_forecast,
        }

    def calculate_roi(self, property_id: UUID, account_id: UUID) -> dict:
        """Рассчитать ROI для объекта (по чистой прибыли)."""
        prop = self.property_repo.get_by_id(property_id, account_id)
        if not prop:
            return {
                "annual_income": Decimal("0"),
                "annual_expenses": Decimal("0"),
                "annual_profit": Decimal("0"),
                "roi": None,
                "payback_years": None,
                "income_is_forecast": False,
            }

        annual_income, income_is_forecast = self.calculate_annual_income(
            property_id, account_id
        )
        annual_expenses = self.calculate_annual_expenses(property_id, account_id)
        return self._roi_payload(
            annual_income, annual_expenses, prop.purchase_price, income_is_forecast
        )

    def calculate_portfolio_roi(self, account_id: UUID) -> dict:
        """Средневзвешенный ROI по портфелю (по чистой прибыли)."""
        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        total_profit = Decimal("0")
        total_price = Decimal("0")
        count_with_price = 0

        for prop in properties.items:
            if prop.purchase_price and prop.purchase_price > 0:
                income, _ = self.calculate_annual_income(prop.id, account_id)
                expenses = self.calculate_annual_expenses(prop.id, account_id)
                total_profit += income - expenses
                total_price += prop.purchase_price
                count_with_price += 1

        if total_price == 0:
            return {"portfolio_roi": None, "properties_with_roi": 0}

        roi = round(float(total_profit / total_price * 100), 1)
        return {"portfolio_roi": roi, "properties_with_roi": count_with_price}

    def calculate_roi_batch(self, account_id: UUID) -> dict[UUID, dict]:
        """Рассчитать ROI для всех объектов аккаунта за один проход."""
        today = date.today()
        year_ago = today - timedelta(days=365)

        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        prop_map = {p.id: p for p in properties.items if p.purchase_price and p.purchase_price > 0}

        contracts = self.contract_repo.list_all_by_account(account_id)
        contract_map: dict[UUID, list[UUID]] = {}
        for c in contracts:
            contract_map.setdefault(c.property_id, []).append(c.id)

        all_payments = self.payment_repo.list_by_account(account_id)
        all_expenses = self.expense_repo.list_by_account(
            account_id, start_date=year_ago, end_date=today
        )

        expenses_by_property: dict[UUID, Decimal] = {}
        for e in all_expenses:
            expenses_by_property[e.property_id] = (
                expenses_by_property.get(e.property_id, Decimal("0")) + e.amount
            )

        result = {}
        for prop_id, prop in prop_map.items():
            total = Decimal("0")
            if prop_id in contract_map:
                for contract_id in contract_map[prop_id]:
                    for p in all_payments:
                        if p.contract_id == contract_id and p.date_paid >= year_ago:
                            total += p.amount

            income_is_forecast = False
            if total == 0:
                active = self.contract_repo.get_active_for_property(prop_id, account_id)
                if active:
                    total = active.rent_amount * 12
                    income_is_forecast = True

            annual_expenses = expenses_by_property.get(prop_id, Decimal("0"))
            result[prop_id] = self._roi_payload(
                total, annual_expenses, prop.purchase_price, income_is_forecast
            )

        return result