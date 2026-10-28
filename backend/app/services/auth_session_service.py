"""Управление жизненным циклом JWT-сессий."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from jose import JWTError
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    decode_access_token,
)
from app.domain.entities import AuthSessionEntity
from app.domain.interfaces import IAuthSessionRepository
from app.db.tenant_context import set_tenant_context


class AuthSessionService:
    """Выдаёт access-токены и проверяет/отзывает связанные сессии."""

    def __init__(
        self, repository: IAuthSessionRepository, session: Session | None = None
    ) -> None:
        self.repository = repository
        self.session = session

    def issue_access_token(self, user_id: UUID, account_id: UUID) -> str:
        """Создать серверную сессию и связанный с ней JWT."""
        now = datetime.now(timezone.utc)
        self.repository.delete_expired(now)
        session = AuthSessionEntity(
            id=uuid4(),
            user_id=user_id,
            account_id=account_id,
            expires_at=now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        self.repository.create(session)
        return create_access_token(
            user_id=str(user_id),
            account_id=str(account_id),
            session_id=str(session.id),
            expires_at=session.expires_at,
        )

    def require_active(self, session_id: UUID, user_id: UUID, account_id: UUID) -> None:
        """Отклонить JWT без активной серверной сессии."""
        if not self.repository.is_active(
            session_id, user_id, account_id, datetime.now(timezone.utc)
        ):
            raise UnauthorizedError("Session is revoked or expired")

    def revoke_access_token(self, token: str) -> None:
        """Отозвать JWT-сессию; некорректный или истёкший токен игнорируется."""
        try:
            payload = decode_access_token(token)
            session_id = UUID(payload["jti"])
            account_id = UUID(payload["account_id"])
        except (JWTError, KeyError, TypeError, ValueError):
            return
        if self.session is not None:
            set_tenant_context(self.session, account_id)
        self.repository.revoke(session_id, datetime.now(timezone.utc))

    def revoke_all_for_user(self, user_id: UUID) -> None:
        """Завершить все активные сессии пользователя."""
        self.repository.revoke_all_for_user(user_id, datetime.now(timezone.utc))
