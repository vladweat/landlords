"""Общие типы пагинации доменного слоя."""

from dataclasses import dataclass
from typing import Any


@dataclass
class PaginatedResult:
    items: list[Any]
    total: int
    page: int
    per_page: int
    pages: int
