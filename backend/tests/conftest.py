"""Общие фикстуры для всех тестов."""

import pytest


@pytest.fixture
def sample_account_id() -> str:
    """Пример account_id для тестов."""
    return "d62828e6-7e44-47e9-8dc5-a2152dec921b"


@pytest.fixture
def sample_user_id() -> str:
    """Пример user_id для тестов."""
    return "d51ca983-631f-445b-9734-dfb33b90966d"
