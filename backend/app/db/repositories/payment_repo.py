"""Реализация репозитория платежей."""

from decimal import Decimal
from typing import Sequence
from uuid import UUID
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session
from app.api.pagination import paginate
from app.domain.pagination import PaginatedResult

from app.db.models.payment_model import PaymentModel
from app.db.models.payment_allocation_event_model import PaymentAllocationEventModel
from app.db.models.payment_allocation_target_model import PaymentAllocationTargetModel
from app.db.models.payment_receipt_event_model import PaymentReceiptEventModel
from app.db.models.payment_receipt_model import PaymentReceiptModel
from app.db.models.rent_charge_model import RentChargeModel
from app.domain.entities import (
    PaymentAllocationEventEntity,
    PaymentEntity,
    PaymentReceiptEntity,
    PaymentReceiptEventEntity,
)
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

    def get_by_id_for_update(self, payment_id: UUID, account_id: UUID) -> PaymentEntity | None:
        """Получить платёж с блокировкой строки."""
        model = (
            self.session.query(PaymentModel)
            .filter_by(id=payment_id, account_id=account_id)
            .with_for_update()
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

    def list_by_contracts(
        self,
        contract_ids: Sequence[UUID],
        account_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[PaymentEntity]:
        """Получить платежи для набора контрактов аккаунта одним запросом."""
        if not contract_ids:
            return []
        query = self.session.query(PaymentModel).filter(
            PaymentModel.account_id == account_id,
            PaymentModel.contract_id.in_(contract_ids),
        )
        if date_from:
            query = query.filter(PaymentModel.date_paid >= date_from)
        if date_to:
            query = query.filter(PaymentModel.date_paid <= date_to)
        models = query.order_by(PaymentModel.date_paid.desc()).all()
        return [model.to_entity() for model in models]

    def list_by_account(
        self,
        account_id: UUID,
        contract_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = 100,
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

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        models = query.all()
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

    def has_financial_history_for_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> bool:
        """Check current payment projections and retained receipt history."""
        if (
            self.session.query(PaymentReceiptModel.id)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .first()
            is not None
        ):
            return True
        return (
            self.session.query(PaymentModel.id)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .first()
            is not None
        )

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

    def create_receipt(self, entity: PaymentReceiptEntity) -> None:
        """Добавить исходный immutable receipt в текущую транзакцию."""
        self.session.add(PaymentReceiptModel.from_entity(entity))
        self.session.flush()

    def create_receipt_event(self, entity: PaymentReceiptEventEntity) -> None:
        """Добавить корректировку или отмену receipt."""
        self.session.add(PaymentReceiptEventModel.from_entity(entity))
        self.session.flush()

    def create_allocation_event(self, entity: PaymentAllocationEventEntity) -> None:
        """Добавить allocation или signed reversal в текущую транзакцию."""
        target = (
            self.session.query(PaymentAllocationTargetModel)
            .filter_by(
                id=entity.rent_charge_id,
                account_id=entity.account_id,
                contract_id=entity.contract_id,
            )
            .first()
        )
        if target is None:
            charge = (
                self.session.query(RentChargeModel)
                .filter_by(
                    id=entity.rent_charge_id,
                    account_id=entity.account_id,
                    contract_id=entity.contract_id,
                )
                .first()
            )
            if charge is None:
                raise ValueError("Allocation target charge not found")
            target = PaymentAllocationTargetModel(
                id=charge.id,
                account_id=charge.account_id,
                contract_id=charge.contract_id,
                due_date=charge.due_date,
                period_start=charge.period_start,
                period_end=charge.period_end,
                original_amount=charge.amount,
                currency=charge.currency,
                created_at=charge.created_at,
            )
            self.session.add(target)
            self.session.flush()
        self.session.add(PaymentAllocationEventModel.from_entity(entity))
        self.session.flush()

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
        model.receipt_id = entity.receipt_id
        model.allocation_event_id = entity.allocation_event_id
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
