"""Реализация репозитория memberships."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.membership_model import MembershipModel
from app.domain.entities import MembershipEntity
from app.domain.interfaces import IMembershipRepository


class MembershipRepository(IMembershipRepository):
    """Реализация репозитория memberships на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, membership_id: UUID) -> MembershipEntity | None:
        """Получить membership по ID."""
        model = self.session.query(MembershipModel).filter_by(id=membership_id).first()
        return model.to_entity() if model else None

    def get_by_user_id(self, user_id: UUID) -> MembershipEntity | None:
        """Получить membership пользователя (v1: один аккаунт)."""
        model = (
            self.session.query(MembershipModel)
            .filter_by(user_id=user_id, is_active=True)
            .first()
        )
        return model.to_entity() if model else None

    def get_by_user_and_account(
        self, user_id: UUID, account_id: UUID
    ) -> MembershipEntity | None:
        """Получить membership по user и account."""
        model = (
            self.session.query(MembershipModel)
            .filter_by(user_id=user_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_account(self, account_id: UUID) -> list[MembershipEntity]:
        """Список участников аккаунта."""
        models = (
            self.session.query(MembershipModel)
            .filter_by(account_id=account_id)
            .order_by(MembershipModel.created_at.asc())
            .all()
        )
        return [m.to_entity() for m in models]

    def create(self, entity: MembershipEntity) -> MembershipEntity:
        """Создать membership."""
        model = MembershipModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: MembershipEntity) -> MembershipEntity:
        """Обновить membership."""
        model = self.session.query(MembershipModel).filter_by(id=entity.id).first()
        if not model:
            raise ValueError("Membership not found")
        model.role = entity.role
        model.is_active = entity.is_active
        self.session.flush()
        return model.to_entity()

    def delete(self, membership_id: UUID) -> None:
        """Удалить membership."""
        self.session.query(MembershipModel).filter_by(id=membership_id).delete()
        self.session.flush()

    def count_active_by_account(self, account_id: UUID) -> int:
        """Количество активных участников аккаунта."""
        return (
            self.session.query(MembershipModel)
            .filter_by(account_id=account_id, is_active=True)
            .count()
        )
