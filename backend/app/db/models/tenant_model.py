"""ORM-модель арендатора."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import TenantEntity


class TenantModel(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_entity(self) -> TenantEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return TenantEntity(
            id=self.id,
            account_id=self.account_id,
            full_name=self.full_name,
            email=self.email,
            phone=self.phone,
            notes=self.notes,
            is_active=self.is_active,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: TenantEntity) -> "TenantModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            full_name=entity.full_name,
            email=entity.email,
            phone=entity.phone,
            notes=entity.notes,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )