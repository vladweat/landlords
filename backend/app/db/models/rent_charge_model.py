"""ORM-модель начисления арендной платы."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import RentChargeEntity


class RentChargeModel(TimestampMixin, Base):
    __tablename__ = "rent_charges"
    
    __table_args__ = (
        Index("ix_rent_charges_contract_status", "contract_id", "status"),
        Index("ix_rent_charges_due_date_status", "due_date", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    def to_entity(self) -> RentChargeEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return RentChargeEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            due_date=self.due_date,
            period_start=self.period_start,
            period_end=self.period_end,
            amount=self.amount,
            currency=self.currency,
            status=self.status,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: RentChargeEntity) -> "RentChargeModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            due_date=entity.due_date,
            period_start=entity.period_start,
            period_end=entity.period_end,
            amount=entity.amount,
            currency=entity.currency,
            status=entity.status,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )