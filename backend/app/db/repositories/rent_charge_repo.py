"""Реализация репозитория начислений."""

from decimal import Decimal
from uuid import UUID
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.rent_charge_model import RentChargeModel
from app.domain.entities import RentChargeEntity
from app.domain.interfaces import IRentChargeRepository


class RentChargeRepository(IRentChargeRepository):
    """Реализация репозитория начислений на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, charge_id: UUID, account_id: UUID) -> RentChargeEntity | None:
        """Получить начисление по ID."""
        model = (
            self.session.query(RentChargeModel)
            .filter_by(id=charge_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> list[RentChargeEntity]:
        """Список начислений по контракту."""
        models = (
            self.session.query(RentChargeModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .order_by(RentChargeModel.due_date)
            .all()
        )
        return [m.to_entity() for m in models]

    def list_by_account(self, account_id: UUID) -> list[RentChargeEntity]:
        """Список всех начислений аккаунта."""
        models = (
            self.session.query(RentChargeModel)
            .filter_by(account_id=account_id)
            .order_by(RentChargeModel.due_date.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def create(self, entity: RentChargeEntity) -> RentChargeEntity:
        """Создать начисление."""
        model = RentChargeModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: RentChargeEntity) -> RentChargeEntity:
        """Обновить начисление."""
        model = (
            self.session.query(RentChargeModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("RentCharge not found")
        model.due_date = entity.due_date
        model.period_start = entity.period_start
        model.period_end = entity.period_end
        model.amount = entity.amount
        model.currency = entity.currency
        model.status = entity.status
        self.session.flush()
        return model.to_entity()

    def delete(self, charge_id: UUID, account_id: UUID) -> None:
        """Удалить начисление."""
        model = (
            self.session.query(RentChargeModel)
            .filter_by(id=charge_id, account_id=account_id)
            .first()
        )
        if model:
            self.session.delete(model)
            self.session.flush()

    def update_status(
        self, charge_id: UUID, account_id: UUID, status: str
    ) -> RentChargeEntity:
        """Обновить статус начисления."""
        model = (
            self.session.query(RentChargeModel)
            .filter_by(id=charge_id, account_id=account_id)
            .first()
        )
        if not model:
            raise ValueError("RentCharge not found")
        model.status = status
        self.session.flush()
        return model.to_entity()
    
    

    def get_total_expected_for_month(
        self, account_id: UUID, year: int, month: int
    ) -> Decimal:
        """Общая сумма начислений за месяц."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        result = (
            self.session.query(func.coalesce(func.sum(RentChargeModel.amount), 0))
            .filter(
                RentChargeModel.account_id == account_id,
                RentChargeModel.due_date >= start_date,
                RentChargeModel.due_date < end_date,
            )
            .scalar()
        )
        return Decimal(str(result))


    def get_total_outstanding(self, account_id: UUID) -> Decimal:
        """Общая сумма неоплаченных начислений (status != 'paid')."""
        result = (
            self.session.query(func.coalesce(func.sum(RentChargeModel.amount), 0))
            .filter(
                RentChargeModel.account_id == account_id,
                RentChargeModel.status != "paid",
            )
            .scalar()
        )
        return Decimal(str(result))
    
    def get_overdue_total_amount(self, account_id: UUID) -> Decimal:
        """Общая сумма просроченных начислений."""
        result = (
            self.session.query(func.coalesce(func.sum(RentChargeModel.amount), 0))
            .filter(
                RentChargeModel.account_id == account_id,
                RentChargeModel.status == "overdue",
            )
            .scalar()
        )
        return Decimal(str(result))
    
    def list_unpaid_for_contract_for_update(
        self, contract_id: UUID, account_id: UUID
    ) -> list[RentChargeEntity]:
        """Получить неоплаченные charges с блокировкой строк."""
        models = (
            self.session.query(RentChargeModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .filter(RentChargeModel.status != "paid")
            .order_by(RentChargeModel.due_date)
            .with_for_update()
            .all()
        )
        return [m.to_entity() for m in models]
    
    def get_by_id_for_update(self, charge_id: UUID, account_id: UUID) -> RentChargeEntity | None:
        """Получить charge с блокировкой строки."""
        model = (
            self.session.query(RentChargeModel)
            .filter_by(id=charge_id, account_id=account_id)
            .with_for_update()
            .first()
        )
        return model.to_entity() if model else None