"""ORM-модель квитанции (инвойса) по начислению."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import InvoiceEntity


class InvoiceModel(TimestampMixin, Base):
    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    charge_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rent_charges.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    public_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )

    def to_entity(self) -> InvoiceEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return InvoiceEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            charge_id=self.charge_id,
            public_token=self.public_token,
            document_id=self.document_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: InvoiceEntity) -> "InvoiceModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            charge_id=entity.charge_id,
            public_token=entity.public_token,
            document_id=entity.document_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
