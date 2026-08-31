"""Реализация репозитория арендаторов."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.tenant_model import TenantModel
from app.domain.entities import TenantEntity
from app.domain.interfaces import ITenantRepository
from app.api.pagination import PaginatedResult, paginate

class TenantRepository(ITenantRepository):
    """Реализация репозитория арендаторов на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, tenant_id: UUID, account_id: UUID) -> TenantEntity | None:
        """Получить арендатора по ID с проверкой account_id."""
        model = (
            self.session.query(TenantModel)
            .filter_by(id=tenant_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_account(
        self,
        account_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> PaginatedResult:
        """Список арендаторов с пагинацией и поиском."""
        from app.api.pagination import paginate

        query = (
            self.session.query(TenantModel)
            .filter_by(account_id=account_id)
            .order_by(TenantModel.full_name)
        )

        if search:
            query = query.filter(TenantModel.full_name.ilike(f"%{search}%"))

        return paginate(query, page, per_page)

    def create(self, entity: TenantEntity) -> TenantEntity:
        """Создать арендатора."""
        model = TenantModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: TenantEntity) -> TenantEntity:
        """Обновить арендатора."""
        model = (
            self.session.query(TenantModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Tenant not found")
        model.full_name = entity.full_name
        model.email = entity.email
        model.phone = entity.phone
        model.notes = entity.notes
        model.is_active = entity.is_active
        self.session.flush()
        return model.to_entity()

    def delete(self, tenant_id: UUID, account_id: UUID) -> None:
        """Удалить арендатора."""
        self.session.query(TenantModel).filter_by(
            id=tenant_id, account_id=account_id
        ).delete()
        self.session.flush()