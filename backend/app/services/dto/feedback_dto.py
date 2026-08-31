"""DTO для обратной связи."""

from pydantic import BaseModel, Field


class FeedbackCreateDTO(BaseModel):
    category: str = Field(..., pattern="^(bug|feature|question|other)$")
    message: str = Field(..., max_length=2000)


class FeedbackDTO(BaseModel):
    id: str
    message: str
