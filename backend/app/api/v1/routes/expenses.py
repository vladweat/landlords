"""Маршруты для расходов по объектам."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_account_id, get_property_expense_service, require_permissions
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.api.mappers import to_dto
from app.api.v1.schemas.property_expense_schema import (
    PropertyExpenseCreateRequest,
    PropertyExpenseListResponse,
    PropertyExpenseResponse,
    PropertyExpenseSingleResponse,
    PropertyExpenseUpdateRequest,
)
from app.services.dto.property_expense_dto import (
    PropertyExpenseCreateDTO,
    PropertyExpenseUpdateDTO,
)
from app.services.property_expense_service import PropertyExpenseService

router = APIRouter(prefix="/v1/expenses", tags=["Expenses"])


@router.get("", response_model=PropertyExpenseListResponse)
def list_expenses(
    property_id: UUID | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyExpenseService = Depends(get_property_expense_service),
) -> dict:
    """Получить список расходов."""
    expenses = service.list_expenses(
        account_id,
        property_id=property_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {
        "status": "success",
        "data": [PropertyExpenseResponse.model_validate(e) for e in expenses],
    }


@router.post("", response_model=PropertyExpenseSingleResponse, status_code=201)
def create_expense(
    body: PropertyExpenseCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyExpenseService = Depends(get_property_expense_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_EXPENSES)),
) -> dict:
    """Создать расход."""
    dto = to_dto(body, PropertyExpenseCreateDTO)
    created = service.create_expense(account_id, dto)
    return {
        "status": "success",
        "data": PropertyExpenseResponse.model_validate(created),
    }


@router.put("/{expense_id}", response_model=PropertyExpenseSingleResponse)
def update_expense(
    expense_id: UUID,
    body: PropertyExpenseUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyExpenseService = Depends(get_property_expense_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_EXPENSES)),
) -> dict:
    """Обновить расход."""
    dto = to_dto(body, PropertyExpenseUpdateDTO)
    updated = service.update_expense(expense_id, account_id, dto)
    return {
        "status": "success",
        "data": PropertyExpenseResponse.model_validate(updated),
    }


@router.delete("/{expense_id}", status_code=204)
def delete_expense(
    expense_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyExpenseService = Depends(get_property_expense_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_EXPENSES)),
) -> None:
    """Удалить расход."""
    service.delete_expense(expense_id, account_id)
