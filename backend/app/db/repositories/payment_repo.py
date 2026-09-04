"""Реализация репозитория платежей."""

from decimal import Decimal
from uuid import UUID
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.pagination import paginate
from app.domain.pagination import PaginatedResult

from app.db.models.payment_model import PaymentModel
from app.domain.entities import PaymentEntity
from app.domain.interfaces import IPaymentRepository


class PaymentRepository(IPaymentRepository):
    """Реализация репозитория платежей на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, payment_id: UUID, account_id: UUID) -> PaymentEntity | None:
        """Получить платёж по ID."""
        model = (
            self.session.query(PaymentModel)
            .filter_by(id=payment_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> list[PaymentEntity]:
        """Список платежей по контракту."""
        models = (
            self.session.query(PaymentModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .order_by(PaymentModel.date_paid.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def list_by_account(
        self,
        account_id: UUID,
        contract_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[PaymentEntity]:
        """Список платежей аккаунта с фильтрацией."""
        query = (
            self.session.query(PaymentModel)
            .filter_by(account_id=account_id)
            .order_by(PaymentModel.date_paid.desc())
        )

        if contract_id:
            query = query.filter_by(contract_id=contract_id)
        if start_date:
            query = query.filter(PaymentModel.date_paid >= start_date)
        if end_date:
            query = query.filter(PaymentModel.date_paid <= end_date)

        models = query.offset(offset).limit(limit).all()
        return [m.to_entity() for m in models]

    def list_by_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> list[PaymentEntity]:
        """Список платежей по начислению."""
        models = (
            self.session.query(PaymentModel)
            .filter_by(rent_charge_id=charge_id, account_id=account_id)
            .order_by(PaymentModel.date_paid.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def get_total_paid_for_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> Decimal:
        """Общая сумма платежей по начислению."""
        result = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter_by(rent_charge_id=charge_id, account_id=account_id)
            .scalar()
        )
        return Decimal(str(result))

    def list_unlinked_for_contract_for_update(
        self, contract_id: UUID, account_id: UUID
    ) -> list[PaymentEntity]:
        """Авансы по контракту с блокировкой строк (FIFO по date_paid, created_at)."""
        models = (
            self.session.query(PaymentModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .filter(PaymentModel.rent_charge_id.is_(None))
            .order_by(PaymentModel.date_paid.asc(), PaymentModel.created_at.asc())
            .with_for_update()
            .all()
        )
        return [m.to_entity() for m in models]

    def get_total_unallocated_for_account(self, account_id: UUID) -> Decimal:
        """Сумма неаллоцированных платежей (авансов) по аккаунту."""
        result = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.rent_charge_id.is_(None),
            )
            .scalar()
        )
        return Decimal(str(result))

    def create(self, entity: PaymentEntity) -> PaymentEntity:
        """Создать платёж."""
        model = PaymentModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: PaymentEntity) -> PaymentEntity:
        """Обновить платёж."""
        model = (
            self.session.query(PaymentModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Payment not found")
        model.date_paid = entity.date_paid
        model.amount = entity.amount
        model.method = entity.method
        model.note = entity.note
        model.rent_charge_id = entity.rent_charge_id
        self.session.flush()
        return model.to_entity()

    def delete(self, payment_id: UUID, account_id: UUID) -> None:
        """Удалить платёж."""
        self.session.query(PaymentModel).filter_by(
            id=payment_id, account_id=account_id
        ).delete()
        self.session.flush()
        


    def get_total_paid_for_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> Decimal:
        """Общая сумма платежей по контракту."""
        result = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter_by(contract_id=contract_id, account_id=account_id)
            .scalar()
        )
        return Decimal(str(result))


    def get_total_paid_for_month(
        self, account_id: UUID, year: int, month: int
    ) -> Decimal:
        """Общая сумма платежей за указанный месяц."""
        start_date = date(year, month, 1)
        # Вычисляем последний день месяца
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)

        result = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.date_paid >= start_date,
                PaymentModel.date_paid < end_date,
            )
            .scalar()
        )
        return Decimal(str(result))
    
    def get_monthly_income(self, account_id: UUID, year: int, month: int) -> Decimal:
        """Доход за указанный месяц."""
        from datetime import date as dt_date

        start = dt_date(year, month, 1)
        if month == 12:
            end = dt_date(year + 1, 1, 1)
        else:
            end = dt_date(year, month + 1, 1)

        result = (
            self.session.query(func.coalesce(func.sum(PaymentModel.amount), 0))
            .filter(
                PaymentModel.account_id == account_id,
                PaymentModel.date_paid >= start,
                PaymentModel.date_paid < end,
            )
            .scalar()
        )
        return Decimal(str(result))

    
    def get_by_tenant(self, tenant_id: UUID, account_id: UUID) -> list[PaymentEntity]:
        """Получить все платежи арендатора."""
        from app.db.models.contract_model import ContractModel

        models = (
            self.session.query(PaymentModel)
            .join(ContractModel, PaymentModel.contract_id == ContractModel.id)
            .filter(
                ContractModel.tenant_id == tenant_id,
                PaymentModel.account_id == account_id,
            )
            .order_by(PaymentModel.date_paid)
            .all()
        )
        return [m.to_entity() for m in models]
