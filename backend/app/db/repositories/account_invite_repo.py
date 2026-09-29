"""Репозиторий приглашений в аккаунт."""

from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from app.db.models.account_invite_model import AccountInviteModel
from app.domain.entities import AccountInviteEntity
from app.domain.interfaces import IAccountInviteRepository
from sqlalchemy.orm import Session


class AccountInviteRepository(IAccountInviteRepository):
    """SQLAlchemy-реализация приглашений."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: AccountInviteEntity) -> AccountInviteEntity:
        """Создать приглашение."""
        model = AccountInviteModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def get_by_id(self, invite_id: UUID, account_id: UUID) -> AccountInviteEntity | None:
        """Получить приглашение по id в рамках аккаунта."""
        model = (
            self.session.query(AccountInviteModel)
            .filter_by(id=invite_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def get_by_token(self, token: str) -> AccountInviteEntity | None:
        """Получить приглашение по токену."""
        model = self.session.query(AccountInviteModel).filter_by(token=token).first()
        return model.to_entity() if model else None

    def get_pending_by_email(
        self, account_id: UUID, email: str
    ) -> AccountInviteEntity | None:
        """Активное (не принятое) приглашение по email в аккаунте."""
        model = (
            self.session.query(AccountInviteModel)
            .filter_by(account_id=account_id, email=email.lower())
            .filter(AccountInviteModel.accepted_at.is_(None))
            .first()
        )
        return model.to_entity() if model else None

    def list_pending(self, account_id: UUID) -> Sequence[AccountInviteEntity]:
        """Список непринятых приглашений аккаунта."""
        now = datetime.now(timezone.utc)
        models = (
            self.session.query(AccountInviteModel)
            .filter_by(account_id=account_id)
            .filter(AccountInviteModel.accepted_at.is_(None))
            .filter(AccountInviteModel.expires_at > now)
            .order_by(AccountInviteModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def update(self, entity: AccountInviteEntity) -> AccountInviteEntity:
        """Обновить приглашение."""
        model = self.session.query(AccountInviteModel).filter_by(id=entity.id).first()
        if not model:
            raise ValueError("Invite not found")
        model.email = entity.email
        model.full_name = entity.full_name
        model.role = entity.role
        model.token = entity.token
        model.expires_at = entity.expires_at
        model.accepted_at = entity.accepted_at
        self.session.flush()
        return model.to_entity()

    def delete(self, invite_id: UUID, account_id: UUID) -> None:
        """Удалить приглашение."""
        model = (
            self.session.query(AccountInviteModel)
            .filter_by(id=invite_id, account_id=account_id)
            .first()
        )
        if model:
            self.session.delete(model)
            self.session.flush()
