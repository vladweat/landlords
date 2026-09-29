"""ORM-модель приглашений в аккаунт."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import AccountInviteEntity


class AccountInviteModel(Base, TimestampMixin):
    """Таблица account_invites — invite по ссылке."""

    __tablename__ = "account_invites"
    __table_args__ = (
        UniqueConstraint("token", name="uq_account_invites_token"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invited_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    def to_entity(self) -> AccountInviteEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return AccountInviteEntity(
            id=self.id,
            account_id=self.account_id,
            email=self.email,
            full_name=self.full_name,
            role=self.role,
            token=self.token,
            expires_at=self.expires_at,
            invited_by_user_id=self.invited_by_user_id,
            accepted_at=self.accepted_at,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: AccountInviteEntity) -> "AccountInviteModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            email=entity.email,
            full_name=entity.full_name,
            role=entity.role,
            token=entity.token,
            expires_at=entity.expires_at,
            invited_by_user_id=entity.invited_by_user_id,
            accepted_at=entity.accepted_at,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
