"""Универсальные хелперы для ответов API."""

from typing import Any


def success_response(data: Any) -> dict:
    """Создать успешный ответ.

    Args:
        data: данные для поля data.

    Returns:
        {"status": "success", "data": ...}
    """
    return {"status": "success", "data": data}


def success_list_response(data: list[Any]) -> dict:
    """Создать успешный ответ со списком.

    Args:
        data: список данных.

    Returns:
        {"status": "success", "data": [...]}
    """
    return {"status": "success", "data": data}