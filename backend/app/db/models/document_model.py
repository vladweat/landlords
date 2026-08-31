"""Модель сохранённого документа."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import DocumentEntity


class DocumentModel(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def to_entity(self) -> DocumentEntity:
        return DocumentEntity(
            id=self.id, account_id=self.account_id, contract_id=self.contract_id,
            filename=self.filename, file_path=self.file_path, created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: DocumentEntity) -> "DocumentModel":
        return cls(
            id=entity.id, account_id=entity.account_id, contract_id=entity.contract_id,
            filename=entity.filename, file_path=entity.file_path, created_at=entity.created_at,
        )