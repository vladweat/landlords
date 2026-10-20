"""ORM-модель серверной авторизационной сессии."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base
from app.domain.entities import AuthSessionEntity


class AuthSessionModel(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_expires_at", "expires_at"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def to_entity(self) -> AuthSessionEntity:
        return AuthSessionEntity(
            id=self.id,
            user_id=self.user_id,
            account_id=self.account_id,
            expires_at=self.expires_at,
            revoked_at=self.revoked_at,
            created_at=self.created_at,
        )
