"""ORM-модель контракта аренды."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Index


from app.db.models.base import Base, TimestampMixin
from app.domain.entities import ContractEntity


class ContractModel(TimestampMixin, Base):
    __tablename__ = "contracts"
    
    __table_args__ = (
        Index("ix_contracts_property_status", "property_id", "status"),
        Index("ix_contracts_account_status", "account_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    property_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False, index=True)
    tenant_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    rent_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB", nullable=False)
    billing_period: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    payment_day: Mapped[int] = mapped_column(Integer, nullable=False)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    auto_generate_charges: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    termination_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def to_entity(self) -> ContractEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return ContractEntity(
            id=self.id,
            account_id=self.account_id,
            property_id=self.property_id,
            tenant_id=self.tenant_id,
            start_date=self.start_date,
            end_date=self.end_date,
            rent_amount=self.rent_amount,
            currency=self.currency,
            billing_period=self.billing_period,
            payment_day=self.payment_day,
            deposit_amount=self.deposit_amount,
            auto_generate_charges=self.auto_generate_charges,
            status=self.status,
            termination_reason=self.termination_reason,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: ContractEntity) -> "ContractModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            property_id=entity.property_id,
            tenant_id=entity.tenant_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            rent_amount=entity.rent_amount,
            currency=entity.currency,
            billing_period=entity.billing_period,
            payment_day=entity.payment_day,
            deposit_amount=entity.deposit_amount,
            auto_generate_charges=entity.auto_generate_charges,
            status=entity.status,
            termination_reason=entity.termination_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )