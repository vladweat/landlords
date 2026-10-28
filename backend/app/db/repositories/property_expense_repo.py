"""Реализация репозитория расходов по объектам."""

from datetime import date
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.property_expense_model import PropertyExpenseModel
from app.domain.entities import PropertyExpenseEntity
from app.domain.interfaces import IPropertyExpenseRepository


class PropertyExpenseRepository(IPropertyExpenseRepository):
    """Реализация репозитория расходов на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, expense_id: UUID, account_id: UUID) -> PropertyExpenseEntity | None:
        """Получить расход по ID."""
        model = (
            self.session.query(PropertyExpenseModel)
            .filter_by(id=expense_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_account(
        self,
        account_id: UUID,
        property_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PropertyExpenseEntity]:
        """Список расходов аккаунта с фильтрацией."""
        query = (
            self.session.query(PropertyExpenseModel)
            .filter_by(account_id=account_id)
            .order_by(PropertyExpenseModel.date_incurred.desc())
        )
        if property_id:
            query = query.filter_by(property_id=property_id)
        if start_date:
            query = query.filter(PropertyExpenseModel.date_incurred >= start_date)
        if end_date:
            query = query.filter(PropertyExpenseModel.date_incurred <= end_date)
        return [m.to_entity() for m in query.all()]

    def list_by_property(
        self, property_id: UUID, account_id: UUID
    ) -> list[PropertyExpenseEntity]:
        """Список расходов по объекту."""
        models = (
            self.session.query(PropertyExpenseModel)
            .filter_by(property_id=property_id, account_id=account_id)
            .order_by(PropertyExpenseModel.date_incurred.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def get_total_for_property(
        self,
        property_id: UUID,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Decimal:
        """Сумма расходов по объекту за период."""
        query = self.session.query(
            func.coalesce(func.sum(PropertyExpenseModel.amount), 0)
        ).filter_by(property_id=property_id, account_id=account_id)
        if start_date:
            query = query.filter(PropertyExpenseModel.date_incurred >= start_date)
        if end_date:
            query = query.filter(PropertyExpenseModel.date_incurred <= end_date)
        return Decimal(str(query.scalar()))

    def sum_by_property_ids(
        self,
        property_ids: Sequence[UUID],
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[UUID, Decimal]:
        """Сгруппировать расходы по объектам одним запросом."""
        if not property_ids:
            return {}
        query = (
            self.session.query(
                PropertyExpenseModel.property_id,
                func.coalesce(func.sum(PropertyExpenseModel.amount), 0),
            )
            .filter(
                PropertyExpenseModel.account_id == account_id,
                PropertyExpenseModel.property_id.in_(property_ids),
            )
        )
        if start_date:
            query = query.filter(PropertyExpenseModel.date_incurred >= start_date)
        if end_date:
            query = query.filter(PropertyExpenseModel.date_incurred <= end_date)
        return {property_id: Decimal(str(total)) for property_id, total in query.group_by(
            PropertyExpenseModel.property_id
        ).all()}

    def create(self, entity: PropertyExpenseEntity) -> PropertyExpenseEntity:
        """Создать расход."""
        model = PropertyExpenseModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: PropertyExpenseEntity) -> PropertyExpenseEntity:
        """Обновить расход."""
        model = (
            self.session.query(PropertyExpenseModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Expense not found")
        model.category = entity.category
        model.amount = entity.amount
        model.currency = entity.currency
        model.date_incurred = entity.date_incurred
        model.note = entity.note
        self.session.flush()
        return model.to_entity()

    def delete(self, expense_id: UUID, account_id: UUID) -> None:
        """Удалить расход."""
        self.session.query(PropertyExpenseModel).filter_by(
            id=expense_id, account_id=account_id
        ).delete()
        self.session.flush()
