"""ORM-модель аккаунта."""

from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import AccountEntity


class AccountModel(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    base_currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)

    def to_entity(self) -> AccountEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return AccountEntity(
            id=self.id,
            name=self.name,
            owner_id=self.owner_id,
            base_currency=self.base_currency,
            timezone=self.timezone,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: AccountEntity) -> "AccountModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            name=entity.name,
            owner_id=entity.owner_id,
            base_currency=entity.base_currency,
            timezone=entity.timezone,
            created_at=entity.created_at,
        )