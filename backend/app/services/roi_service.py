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
        """Годовой доход: платежи за 12 месяцев или прогноз по активному договору."""
        year_ago = date.today() - timedelta(days=365)
        contracts = [
            contract for contract in self.contract_repo.list_all_by_account(account_id)
            if contract.property_id == property_id
        ]
        total = Decimal("0")
        if contracts:
            payments = self.payment_repo.list_by_contracts(
                [contract.id for contract in contracts], account_id, date_from=year_ago
            )
            total = sum((payment.amount for payment in payments), Decimal("0"))

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
                "annual_income": format(annual_income, "f"),
                "annual_expenses": format(annual_expenses, "f"),
                "annual_profit": format(annual_profit, "f"),
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
            "annual_income": format(annual_income, "f"),
            "annual_expenses": format(annual_expenses, "f"),
            "annual_profit": format(annual_profit, "f"),
            "roi": roi,
            "payback_years": payback,
            "income_is_forecast": income_is_forecast,
        }

    def calculate_roi(self, property_id: UUID, account_id: UUID) -> dict:
        """Рассчитать ROI для объекта (по чистой прибыли)."""
        prop = self.property_repo.get_by_id(property_id, account_id)
        if not prop:
            return {
                "annual_income": "0",
                "annual_expenses": "0",
                "annual_profit": "0",
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
        """Средневзвешенный ROI по портфелю с пакетной загрузкой данных."""
        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        roi_by_property = self._calculate_roi_batch(properties.items, account_id)
        property_by_id = {prop.id: prop for prop in properties.items}
        total_profit = Decimal("0")
        total_price = Decimal("0")
        for property_id, payload in roi_by_property.items():
            prop = property_by_id[property_id]
            total_profit += Decimal(payload["annual_profit"])
            total_price += prop.purchase_price

        if total_price == 0:
            return {"portfolio_roi": None, "properties_with_roi": 0}
        roi = round(float(total_profit / total_price * 100), 1)
        return {"portfolio_roi": roi, "properties_with_roi": len(roi_by_property)}

    def calculate_roi_batch(self, account_id: UUID) -> dict[UUID, dict]:
        """Рассчитать ROI всех объектов, выполняя чтения пакетно."""
        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        return self._calculate_roi_batch(properties.items, account_id)

    def _calculate_roi_batch(self, properties, account_id: UUID) -> dict[UUID, dict]:
        today = date.today()
        year_ago = today - timedelta(days=365)
        properties_with_price = [
            prop for prop in properties
            if prop.purchase_price and prop.purchase_price > 0
        ]
        property_ids = [prop.id for prop in properties_with_price]
        if not property_ids:
            return {}

        contracts = self.contract_repo.list_all_by_account(account_id)
        contracts_by_property: dict[UUID, list] = {}
        active_by_property = {}
        for contract in contracts:
            contracts_by_property.setdefault(contract.property_id, []).append(contract)
            if contract.status in ("active", "overdue"):
                active_by_property.setdefault(contract.property_id, contract)

        relevant_contracts = [
            contract for prop_id in property_ids
            for contract in contracts_by_property.get(prop_id, [])
        ]
        payments = self.payment_repo.list_by_contracts(
            [contract.id for contract in relevant_contracts], account_id,
            date_from=year_ago,
        )
        payments_by_contract: dict[UUID, Decimal] = {}
        for payment in payments:
            payments_by_contract[payment.contract_id] = (
                payments_by_contract.get(payment.contract_id, Decimal("0")) + payment.amount
            )

        expenses_by_property = self.expense_repo.sum_by_property_ids(
            property_ids, account_id, start_date=year_ago, end_date=today
        )

        result = {}
        for prop in properties_with_price:
            annual_income = sum(
                (payments_by_contract.get(contract.id, Decimal("0"))
                 for contract in contracts_by_property.get(prop.id, [])),
                Decimal("0"),
            )
            income_is_forecast = False
            if annual_income == 0:
                active = active_by_property.get(prop.id)
                if active:
                    annual_income = active.rent_amount * 12
                    income_is_forecast = True

            annual_expenses = expenses_by_property.get(prop.id, Decimal("0"))
            result[prop.id] = self._roi_payload(
                annual_income, annual_expenses, prop.purchase_price, income_is_forecast
            )
        return result
