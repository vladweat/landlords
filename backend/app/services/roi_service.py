"""Сервис расчёта доходности объектов."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.domain.interfaces import IContractRepository, IPaymentRepository, IPropertyRepository


class RoiService:
    """Сервис расчёта ROI для объектов недвижимости."""

    def __init__(
        self,
        property_repo: IPropertyRepository,
        contract_repo: IContractRepository,
        payment_repo: IPaymentRepository,
    ) -> None:
        self.property_repo = property_repo
        self.contract_repo = contract_repo
        self.payment_repo = payment_repo

    def calculate_annual_income(self, property_id: UUID, account_id: UUID) -> Decimal:
        """Годовой доход: реальные платежи за 12 месяцев по всем контрактам объекта."""
        from datetime import date, timedelta

        today = date.today()
        year_ago = today - timedelta(days=365)

        total = Decimal("0")

        # Получаем все контракты по этому объекту
        all_contracts = self.contract_repo.list_all_by_account(account_id)
        for contract in all_contracts:
            if contract.property_id == property_id:
                payments = self.payment_repo.list_by_contract(contract.id, account_id)
                for p in payments:
                    if p.date_paid >= year_ago:
                        total += p.amount

        # Если за 12 месяцев не было платежей — прогноз по активному контракту
        if total == Decimal("0"):
            active = self.contract_repo.get_active_for_property(property_id, account_id)
            if active:
                total = active.rent_amount * 12

        return total

    def calculate_roi(self, property_id: UUID, account_id: UUID) -> dict:
        """Рассчитать ROI для объекта."""
        prop = self.property_repo.get_by_id(property_id, account_id)
        if not prop:
            return {"annual_income": Decimal("0"), "roi": None, "payback_years": None}

        annual_income = self.calculate_annual_income(property_id, account_id)

        if not prop.purchase_price or prop.purchase_price == 0:
            return {
                "annual_income": annual_income,
                "roi": None,
                "payback_years": None,
            }

        roi = round(float(annual_income / prop.purchase_price * 100), 1)
        payback = round(float(prop.purchase_price / annual_income), 1) if annual_income > 0 else None

        return {
            "annual_income": annual_income,
            "roi": roi,
            "payback_years": payback,
        }

    def calculate_portfolio_roi(self, account_id: UUID) -> dict:
        """Средневзвешенный ROI по портфелю."""
        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        total_income = Decimal("0")
        total_price = Decimal("0")
        count_with_price = 0

        for prop in properties.items:
            if prop.purchase_price and prop.purchase_price > 0:
                income = self.calculate_annual_income(prop.id, account_id)
                total_income += income
                total_price += prop.purchase_price
                count_with_price += 1

        if total_price == 0:
            return {"portfolio_roi": None, "properties_with_roi": 0}

        roi = round(float(total_income / total_price * 100), 1)
        return {"portfolio_roi": roi, "properties_with_roi": count_with_price}
    
    def calculate_roi_batch(self, account_id: UUID) -> dict[UUID, dict]:
        """Рассчитать ROI для всех объектов аккаунта за один проход."""
        from datetime import date, timedelta

        today = date.today()
        year_ago = today - timedelta(days=365)

        # Все объекты с ценой
        properties = self.property_repo.list_by_account(account_id, page=1, per_page=1000)
        prop_map = {p.id: p for p in properties.items if p.purchase_price and p.purchase_price > 0}

        # Все контракты аккаунта
        contracts = self.contract_repo.list_all_by_account(account_id)
        contract_map = {}
        for c in contracts:
            if c.property_id not in contract_map:
                contract_map[c.property_id] = []
            contract_map[c.property_id].append(c.id)

        # Все платежи за год одним запросом — нужно добавить метод
        all_payments = self.payment_repo.list_by_account(account_id)

        # Считаем доход по каждому объекту
        result = {}
        for prop_id, prop in prop_map.items():
            total = Decimal("0")
            if prop_id in contract_map:
                for contract_id in contract_map[prop_id]:
                    for p in all_payments:
                        if p.contract_id == contract_id and p.date_paid >= year_ago:
                            total += p.amount

            if total == 0:
                active = self.contract_repo.get_active_for_property(prop_id, account_id)
                if active:
                    total = active.rent_amount * 12

            roi = float(total / prop.purchase_price * 100) if prop.purchase_price else None
            payback = float(prop.purchase_price / total) if total > 0 and prop.purchase_price else None
            result[prop_id] = {
                "annual_income": total,
                "roi": round(roi, 1) if roi else None,
                "payback_years": round(payback, 1) if payback else None,
            }

        return result
    