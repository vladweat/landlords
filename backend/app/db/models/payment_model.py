"""ORM-модель платежа."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import PaymentEntity


class PaymentModel(TimestampMixin, Base):
    __tablename__ = "payments"
    
    __table_args__ = (
        Index("ix_payments_contract_date", "contract_id", "date_paid"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    contract_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, index=True)
    rent_charge_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("rent_charges.id", ondelete="SET NULL"), nullable=True, index=True)
    date_paid: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    method: Mapped[str] = mapped_column(String(20), default="transfer", nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_entity(self) -> PaymentEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return PaymentEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            rent_charge_id=self.rent_charge_id,
            date_paid=self.date_paid,
            amount=self.amount,
            currency=self.currency,
            method=self.method,
            note=self.note,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: PaymentEntity) -> "PaymentModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            rent_charge_id=entity.rent_charge_id,
            date_paid=entity.date_paid,
            amount=entity.amount,
            currency=entity.currency,
            method=entity.method,
            note=entity.note,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )