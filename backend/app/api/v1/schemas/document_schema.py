"""Pydantic-схемы документов и вложений."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


DocumentCategory = Literal["contract_pdf", "passport", "act", "photo", "other"]
DocumentSource = Literal["generated", "uploaded"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contract_id: UUID | None = None
    property_id: UUID | None = None
    filename: str
    title: str
    category: str
    mime_type: str
    size_bytes: int | None = None
    source: str
    created_at: datetime | None = None
    url: str


class DocumentListResponse(BaseModel):
    status: str = "success"
    data: list[DocumentResponse] = Field(default_factory=list)


class DocumentSingleResponse(BaseModel):
    status: str = "success"
    data: DocumentResponse
