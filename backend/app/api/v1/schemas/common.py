"""Общие схемы для ответов."""

from pydantic import BaseModel


class PaginatedData(BaseModel):
    """Данные с пагинацией."""

    items: list
    total: int
    page: int
    per_page: int
    pages: int


class PaginatedResponse(BaseModel):
    """Ответ с пагинацией."""

    status: str = "success"
    data: PaginatedData