"""Репозиторий авторизационных сессий."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.db.models.auth_session_model import AuthSessionModel
from app.domain.entities import AuthSessionEntity
from app.domain.interfaces import IAuthSessionRepository


class AuthSessionRepository(IAuthSessionRepository):
    """SQLAlchemy-реализация хранения сессий."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: AuthSessionEntity) -> AuthSessionEntity:
        model = AuthSessionModel(
            id=entity.id,
            user_id=entity.user_id,
            account_id=entity.account_id,
            expires_at=entity.expires_at,
            revoked_at=entity.revoked_at,
        )
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def is_active(
        self, session_id: UUID, user_id: UUID, account_id: UUID, now: datetime
    ) -> bool:
        query = exists().where(
            AuthSessionModel.id == session_id,
            AuthSessionModel.user_id == user_id,
            AuthSessionModel.account_id == account_id,
            AuthSessionModel.revoked_at.is_(None),
            AuthSessionModel.expires_at > now,
        )
        return bool(self.session.query(query).scalar())

    def revoke(self, session_id: UUID, revoked_at: datetime) -> None:
        self.session.query(AuthSessionModel).filter(
            AuthSessionModel.id == session_id,
            AuthSessionModel.revoked_at.is_(None),
        ).update({AuthSessionModel.revoked_at: revoked_at}, synchronize_session=False)
        self.session.flush()

    def delete_expired(self, now: datetime) -> None:
        self.session.query(AuthSessionModel).filter(
            AuthSessionModel.expires_at <= now
        ).delete(synchronize_session=False)
        self.session.flush()

    def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> None:
        self.session.query(AuthSessionModel).filter(
            AuthSessionModel.user_id == user_id,
            AuthSessionModel.revoked_at.is_(None),
        ).update({AuthSessionModel.revoked_at: revoked_at}, synchronize_session=False)
        self.session.flush()
