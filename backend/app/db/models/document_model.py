"""Модель сохранённого документа / вложения."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import DocumentEntity


class DocumentModel(TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "(contract_id IS NOT NULL AND property_id IS NULL) OR "
            "(contract_id IS NULL AND property_id IS NOT NULL)",
            name="ck_documents_parent",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    property_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False, default="application/pdf")
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="generated")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_entity(self) -> DocumentEntity:
        return DocumentEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            property_id=self.property_id,
            filename=self.filename,
            file_path=self.file_path,
            title=self.title,
            category=self.category,
            mime_type=self.mime_type,
            size_bytes=self.size_bytes,
            source=self.source,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: DocumentEntity) -> "DocumentModel":
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            property_id=entity.property_id,
            filename=entity.filename,
            file_path=entity.file_path,
            title=entity.title,
            category=entity.category,
            mime_type=entity.mime_type,
            size_bytes=entity.size_bytes,
            source=entity.source,
            created_at=entity.created_at,
        )
