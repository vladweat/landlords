"""Реализация репозитория начислений."""

from decimal import Decimal
from typing import Sequence
from uuid import UUID
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
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

    def list_by_contracts(
        self,
        contract_ids: Sequence[UUID],
        account_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[RentChargeEntity]:
        """Получить начисления для набора контрактов аккаунта одним запросом."""
        if not contract_ids:
            return []
        query = self.session.query(RentChargeModel).filter(
            RentChargeModel.account_id == account_id,
            RentChargeModel.contract_id.in_(contract_ids),
        )
        if date_from:
            query = query.filter(RentChargeModel.due_date >= date_from)
        if date_to:
            query = query.filter(RentChargeModel.due_date <= date_to)
        models = query.order_by(RentChargeModel.due_date).all()
        return [model.to_entity() for model in models]

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

    def create_if_absent(self, entity: RentChargeEntity) -> bool:
        """Вставить начисление, если период ещё не существует."""
        values = {
            "id": entity.id,
            "account_id": entity.account_id,
            "contract_id": entity.contract_id,
            "due_date": entity.due_date,
            "period_start": entity.period_start,
            "period_end": entity.period_end,
            "amount": entity.amount,
            "currency": entity.currency,
            "status": entity.status,
        }
        statement = insert(RentChargeModel).values(**values).on_conflict_do_nothing(
            constraint="uq_rent_charges_contract_period"
        )
        result = self.session.execute(statement)
        return result.rowcount == 1

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
        """Сколько ещё ждать: Σ max(0, amount − paid) − авансы, не ниже 0."""
        from app.db.models.payment_model import PaymentModel

        paid_subq = (
            self.session.query(
                PaymentModel.rent_charge_id.label("charge_id"),
                func.coalesce(func.sum(PaymentModel.amount), 0).label("paid"),
            )
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.rent_charge_id.isnot(None),
            )
            .group_by(PaymentModel.rent_charge_id)
            .subquery()
        )
        remainder = func.greatest(
            RentChargeModel.amount - func.coalesce(paid_subq.c.paid, 0),
            0,
        )
        total_remainders = (
            self.session.query(func.coalesce(func.sum(remainder), 0))
            .select_from(RentChargeModel)
            .outerjoin(paid_subq, paid_subq.c.charge_id == RentChargeModel.id)
            .filter(RentChargeModel.account_id == account_id)
            .scalar()
        )
        advances = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.rent_charge_id.is_(None),
            )
            .scalar()
        )
        result = Decimal(str(total_remainders)) - Decimal(str(advances))
        return max(result, Decimal("0"))

    def _overdue_unpaid_base(self, account_id: UUID):
        """Базовый query: начисления с due_date < today и ненулевым остатком (как календарь)."""
        from app.db.models.payment_model import PaymentModel

        today = datetime.now(timezone.utc).date()
        paid_subq = (
            self.session.query(
                PaymentModel.rent_charge_id.label("charge_id"),
                func.coalesce(func.sum(PaymentModel.amount), 0).label("paid"),
            )
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.rent_charge_id.isnot(None),
            )
            .group_by(PaymentModel.rent_charge_id)
            .subquery()
        )
        paid = func.coalesce(paid_subq.c.paid, 0)
        remainder = func.greatest(RentChargeModel.amount - paid, 0)
        query = (
            self.session.query(RentChargeModel, remainder.label("remainder"))
            .select_from(RentChargeModel)
            .outerjoin(paid_subq, paid_subq.c.charge_id == RentChargeModel.id)
            .filter(
                RentChargeModel.account_id == account_id,
                RentChargeModel.due_date < today,
                RentChargeModel.amount > paid,
            )
        )
        return query, remainder

    def get_overdue_total_amount(self, account_id: UUID) -> Decimal:
        """Сумма остатков по просроченным начислениям (не полные amount)."""
        query, remainder = self._overdue_unpaid_base(account_id)
        result = query.with_entities(func.coalesce(func.sum(remainder), 0)).scalar()
        return Decimal(str(result))

    def get_overdue_count(self, account_id: UUID) -> int:
        """Число просроченных начислений с ненулевым остатком."""
        query, _ = self._overdue_unpaid_base(account_id)
        result = query.with_entities(func.count(RentChargeModel.id)).scalar()
        return int(result or 0)
    
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

    def list_for_calendar(
        self, account_id: UUID, date_to: date
    ) -> list[RentChargeEntity]:
        """Неоплаченные начисления с due_date <= date_to."""
        models = (
            self.session.query(RentChargeModel)
            .filter(
                RentChargeModel.account_id == account_id,
                RentChargeModel.status != "paid",
                RentChargeModel.due_date <= date_to,
            )
            .order_by(RentChargeModel.due_date)
            .all()
        )
        return [m.to_entity() for m in models]
