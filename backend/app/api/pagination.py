from dataclasses import dataclass
from math import ceil
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query


class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


@dataclass
class PaginatedResult:
    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int


def paginate(query: Query, page: int, per_page: int) -> PaginatedResult:
    total = query.count()
    pages = ceil(total / per_page) if per_page > 0 else 0
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return PaginatedResult(
        items=items, total=total, page=page, per_page=per_page, pages=pages,
    )