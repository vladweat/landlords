from typing import Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.account_model import AccountModel
from app.domain.entities import AccountEntity
from app.domain.interfaces import IAccountRepository


class AccountRepository(IAccountRepository):
    """Реализация репозитория аккаунтов на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, account_id: UUID) -> AccountEntity | None:
        """Получить аккаунт по ID."""
        model = self.session.query(AccountModel).filter_by(id=account_id).first()
        return model.to_entity() if model else None

    def get_by_owner_id(self, owner_id: UUID) -> AccountEntity | None:
        """Получить аккаунт по владельцу."""
        model = self.session.query(AccountModel).filter_by(owner_id=owner_id).first()
        return model.to_entity() if model else None  # ← добавил ()

    def create(self, entity: AccountEntity) -> AccountEntity:
        """Создать аккаунт."""
        model = AccountModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: AccountEntity) -> AccountEntity:
        """Обновить аккаунт."""
        model = self.session.query(AccountModel).filter_by(id=entity.id).first()
        if not model:
            raise ValueError("Account not found")
        model.name = entity.name
        model.base_currency = entity.base_currency
        model.timezone = entity.timezone
        model.payment_details = entity.payment_details
        self.session.flush()
        return model.to_entity()

    def list_all(self) -> Sequence[AccountEntity]:
        """Все аккаунты (для фоновых задач)."""
        models = self.session.query(AccountModel).all()
        return [m.to_entity() for m in models]