"""ORM-модель пользователя."""

from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import UserEntity


class UserModel(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def to_entity(self) -> UserEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return UserEntity(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            full_name=self.full_name,
            phone=self.phone,
            is_active=self.is_active,
            created_at=self.created_at,
        )

    @classmethod
    def from_entity(cls, entity: UserEntity) -> "UserModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            email=entity.email,
            password_hash=entity.password_hash,
            full_name=entity.full_name,
            phone=entity.phone,
            is_active=entity.is_active,
            created_at=entity.created_at,
        )
