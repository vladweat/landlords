"""Мапперы для преобразования API-схем в DTO."""

from pydantic import BaseModel


def to_dto(schema: BaseModel, dto_class: type[BaseModel]) -> BaseModel:
    """Преобразовать API-схему в DTO через model_dump.

    Args:
        schema: Pydantic-схема запроса.
        dto_class: класс DTO.

    Returns:
        Экземпляр DTO.
    """
    return dto_class(**schema.model_dump())