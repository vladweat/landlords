"""ORM-модель заявки арендатора «я оплатил»."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import PaymentClaimEntity


class PaymentClaimModel(TimestampMixin, Base):
    __tablename__ = "payment_claims"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    charge_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rent_charges.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def to_entity(self) -> PaymentClaimEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return PaymentClaimEntity(
            id=self.id,
            account_id=self.account_id,
            contract_id=self.contract_id,
            charge_id=self.charge_id,
            amount=self.amount,
            note=self.note,
            status=self.status,
            resolved_at=self.resolved_at,
            resolved_by=self.resolved_by,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: PaymentClaimEntity) -> "PaymentClaimModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            contract_id=entity.contract_id,
            charge_id=entity.charge_id,
            amount=entity.amount,
            note=entity.note,
            status=entity.status,
            resolved_at=entity.resolved_at,
            resolved_by=entity.resolved_by,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
