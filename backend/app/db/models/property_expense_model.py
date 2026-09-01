"""ORM-модель расхода по объекту."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import PropertyExpenseEntity


class PropertyExpenseModel(TimestampMixin, Base):
    __tablename__ = "property_expenses"

    __table_args__ = (
        Index("ix_property_expenses_property_date", "property_id", "date_incurred"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    property_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    date_incurred: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_entity(self) -> PropertyExpenseEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return PropertyExpenseEntity(
            id=self.id,
            account_id=self.account_id,
            property_id=self.property_id,
            category=self.category,
            amount=self.amount,
            currency=self.currency,
            date_incurred=self.date_incurred,
            note=self.note,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: PropertyExpenseEntity) -> "PropertyExpenseModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            property_id=entity.property_id,
            category=entity.category,
            amount=entity.amount,
            currency=entity.currency,
            date_incurred=entity.date_incurred,
            note=entity.note,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
