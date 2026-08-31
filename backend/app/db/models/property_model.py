"""ORM-модель объекта недвижимости."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import PropertyEntity


class PropertyModel(TimestampMixin, Base):
    """Таблица properties."""

    __tablename__ = "properties"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    street: Mapped[str] = mapped_column(String(500), nullable=False)
    house: Mapped[str] = mapped_column(String(50), nullable=False)
    building: Mapped[str | None] = mapped_column(String(50), nullable=True)
    apartment: Mapped[str | None] = mapped_column(String(50), nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    size_m2: Mapped[float] = mapped_column(nullable=False)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    def to_entity(self) -> PropertyEntity:
        return PropertyEntity(
            id=self.id, account_id=self.account_id,
            city=self.city, street=self.street, house=self.house,
            building=self.building, apartment=self.apartment,
            type=self.type, size_m2=self.size_m2,
            purchase_price=self.purchase_price, status=self.status,
            created_at=self.created_at, updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: PropertyEntity) -> "PropertyModel":
        return cls(
            id=entity.id, account_id=entity.account_id,
            city=entity.city, street=entity.street, house=entity.house,
            building=entity.building, apartment=entity.apartment,
            type=entity.type, size_m2=entity.size_m2,
            purchase_price=entity.purchase_price, status=entity.status,
            created_at=entity.created_at, updated_at=entity.updated_at,
        )