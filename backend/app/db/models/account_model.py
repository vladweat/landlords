"""ORM-модель аккаунта."""

from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
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
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    subscription_status: Mapped[str] = mapped_column(
        String(32), default="none", nullable=False
    )
    subscription_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    yookassa_payment_method_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    yookassa_last_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    yookassa_renewal_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    yookassa_renewal_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    yookassa_renewal_idempotence_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    yookassa_renewal_payment_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    yookassa_renewal_status: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )

    def to_entity(self) -> AccountEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return AccountEntity(
            id=self.id,
            name=self.name,
            owner_id=self.owner_id,
            base_currency=self.base_currency,
            timezone=self.timezone,
            payment_details=self.payment_details,
            plan=self.plan,
            subscription_status=self.subscription_status,
            subscription_period_end=self.subscription_period_end,
            yookassa_payment_method_id=self.yookassa_payment_method_id,
            yookassa_last_payment_id=self.yookassa_last_payment_id,
            yookassa_renewal_period_end=self.yookassa_renewal_period_end,
            yookassa_renewal_started_at=self.yookassa_renewal_started_at,
            yookassa_renewal_idempotence_key=self.yookassa_renewal_idempotence_key,
            yookassa_renewal_payment_id=self.yookassa_renewal_payment_id,
            yookassa_renewal_status=self.yookassa_renewal_status,
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
            payment_details=entity.payment_details,
            plan=entity.plan,
            subscription_status=entity.subscription_status,
            subscription_period_end=entity.subscription_period_end,
            yookassa_payment_method_id=entity.yookassa_payment_method_id,
            yookassa_last_payment_id=entity.yookassa_last_payment_id,
            yookassa_renewal_period_end=entity.yookassa_renewal_period_end,
            yookassa_renewal_started_at=entity.yookassa_renewal_started_at,
            yookassa_renewal_idempotence_key=entity.yookassa_renewal_idempotence_key,
            yookassa_renewal_payment_id=entity.yookassa_renewal_payment_id,
            yookassa_renewal_status=entity.yookassa_renewal_status,
            created_at=entity.created_at,
        )
