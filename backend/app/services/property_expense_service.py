"""Сервис управления расходами по объектам."""

from datetime import date
from uuid import UUID, uuid4

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import PropertyExpenseEntity
from app.domain.interfaces import IPropertyExpenseRepository, IPropertyRepository
from app.services.dto.property_expense_dto import (
    PropertyExpenseCreateDTO,
    PropertyExpenseDTO,
    PropertyExpenseUpdateDTO,
)


class PropertyExpenseService:
    """Сервис управления расходами по объектам."""

    def __init__(
        self,
        expense_repo: IPropertyExpenseRepository,
        property_repo: IPropertyRepository,
    ) -> None:
        self.expense_repo = expense_repo
        self.property_repo = property_repo

    def list_expenses(
        self,
        account_id: UUID,
        property_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PropertyExpenseDTO]:
        """Получить список расходов аккаунта с фильтрацией."""
        entities = self.expense_repo.list_by_account(
            account_id=account_id,
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [PropertyExpenseDTO.model_validate(e) for e in entities]

    def create_expense(
        self, account_id: UUID, dto: PropertyExpenseCreateDTO
    ) -> PropertyExpenseDTO:
        """Создать расход по объекту."""
        prop = self.property_repo.get_by_id(dto.property_id, account_id)
        if not prop:
            raise NotFoundError(f"Property with id={dto.property_id} not found")

        if dto.amount <= 0:
            raise ValidationError("Expense amount must be greater than 0")

        entity = PropertyExpenseEntity(
            id=uuid4(),
            account_id=account_id,
            property_id=dto.property_id,
            category=dto.category,
            amount=dto.amount,
            currency=dto.currency,
            date_incurred=dto.date_incurred,
            note=dto.note,
        )
        created = self.expense_repo.create(entity)
        return PropertyExpenseDTO.model_validate(created)

    def update_expense(
        self, expense_id: UUID, account_id: UUID, dto: PropertyExpenseUpdateDTO
    ) -> PropertyExpenseDTO:
        """Обновить расход."""
        entity = self.expense_repo.get_by_id(expense_id, account_id)
        if not entity:
            raise NotFoundError(f"Expense with id={expense_id} not found")

        if dto.category is not None:
            entity.category = dto.category
        if dto.amount is not None:
            if dto.amount <= 0:
                raise ValidationError("Expense amount must be greater than 0")
            entity.amount = dto.amount
        if dto.date_incurred is not None:
            entity.date_incurred = dto.date_incurred
        if dto.note is not None:
            entity.note = dto.note

        updated = self.expense_repo.update(entity)
        return PropertyExpenseDTO.model_validate(updated)

    def delete_expense(self, expense_id: UUID, account_id: UUID) -> None:
        """Удалить расход."""
        entity = self.expense_repo.get_by_id(expense_id, account_id)
        if not entity:
            raise NotFoundError(f"Expense with id={expense_id} not found")
        self.expense_repo.delete(expense_id, account_id)
