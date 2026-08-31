"""Реализация репозитория пользователей."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.user_model import UserModel
from app.domain.entities import UserEntity
from app.domain.interfaces import IUserRepository


class UserRepository(IUserRepository):
    """Реализация репозитория пользователей на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: UUID) -> UserEntity | None:
        """Получить пользователя по ID."""
        model = self.session.query(UserModel).filter_by(id=user_id).first()
        return model.to_entity() if model else None

    def get_by_email(self, email: str) -> UserEntity | None:
        """Получить пользователя по email."""
        model = self.session.query(UserModel).filter_by(email=email).first()
        return model.to_entity() if model else None

    def create(self, entity: UserEntity) -> UserEntity:
        """Создать пользователя."""
        model = UserModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()
    
    def update(self, entity: UserEntity) -> UserEntity:
        """Обновить пользователя."""
        model = self.session.query(UserModel).filter_by(id=entity.id).first()
        if not model:
            raise ValueError("User not found")
        model.email = entity.email
        model.password_hash = entity.password_hash
        model.full_name = entity.full_name
        model.is_active = entity.is_active
        self.session.flush()
        return model.to_entity()


    def delete(self, user_id: UUID) -> None:
        """Удалить пользователя."""
        self.session.query(UserModel).filter_by(id=user_id).delete()
        self.session.flush()