"""Pydantic-схемы для обратной связи."""

from pydantic import BaseModel, Field


class FeedbackCreateRequest(BaseModel):
    """Запрос на создание обратной связи."""

    category: str = Field(..., pattern="^(bug|feature|question|other)$")
    message: str = Field(..., max_length=2000)