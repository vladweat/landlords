"""Pydantic-схемы для расходов по объектам."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ExpenseCategory = Literal["utilities", "repair", "tax", "realtor_fee", "other"]


class PropertyExpenseResponse(BaseModel):
    """Ответ с данными расхода."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    property_id: UUID
    category: str
    amount: Decimal
    currency: str
    date_incurred: date
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class PropertyExpenseCreateRequest(BaseModel):
    """Запрос на создание расхода."""

    property_id: UUID
    category: ExpenseCategory
    amount: Decimal = Field(..., gt=0)
    date_incurred: date
    currency: str = "RUB"
    note: str | None = None


class PropertyExpenseUpdateRequest(BaseModel):
    """Запрос на обновление расхода."""

    category: ExpenseCategory | None = None
    amount: Decimal | None = Field(None, gt=0)
    date_incurred: date | None = None
    note: str | None = None


class PropertyExpenseListResponse(BaseModel):
    """Ответ со списком расходов."""

    status: str = "success"
    data: list[PropertyExpenseResponse]


class PropertyExpenseSingleResponse(BaseModel):
    """Ответ с одним расходом."""

    status: str = "success"
    data: PropertyExpenseResponse
