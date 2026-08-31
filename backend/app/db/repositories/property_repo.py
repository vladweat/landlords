"""Реализация репозитория объектов недвижимости."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.property_model import PropertyModel
from app.domain.entities import PropertyEntity
from app.domain.interfaces import IPropertyRepository
from app.api.pagination import PaginatedResult, paginate
from sqlalchemy import func

class PropertyRepository(IPropertyRepository):
    """Реализация репозитория недвижимости на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, property_id: UUID, account_id: UUID) -> PropertyEntity | None:
        """Получить объект по ID с проверкой account_id."""
        model = (
            self.session.query(PropertyModel)
            .filter_by(id=property_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_account(
        self,
        account_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        property_type: str | None = None,
    ) -> PaginatedResult:
        """Список объектов с пагинацией и поиском."""
        from app.api.pagination import paginate

        query = (
            self.session.query(PropertyModel)
            .filter_by(account_id=account_id)
            .order_by(PropertyModel.created_at.desc())
        )

        if search:
            query = query.filter(func.concat(PropertyModel.city, " ", PropertyModel.street, " ", PropertyModel.house).ilike(f"%{search}%"))
        if property_type:
            query = query.filter_by(type=property_type)

        return paginate(query, page, per_page)

    def create(self, entity: PropertyEntity) -> PropertyEntity:
        """Создать объект недвижимости."""
        model = PropertyModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: PropertyEntity) -> PropertyEntity:
        model = (
            self.session.query(PropertyModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Property not found")
        model.city = entity.city
        model.street = entity.street
        model.house = entity.house
        model.building = entity.building
        model.apartment = entity.apartment
        model.type = entity.type
        model.size_m2 = entity.size_m2
        model.purchase_price = entity.purchase_price
        model.status = entity.status
        self.session.flush()
        return model.to_entity()

    def delete(self, property_id: UUID, account_id: UUID) -> None:
        """Удалить объект недвижимости."""
        self.session.query(PropertyModel).filter_by(
            id=property_id, account_id=account_id
        ).delete()
        self.session.flush()
        
    def count_active(self, account_id: UUID) -> int:
        """Количество активных объектов."""
        return (
            self.session.query(PropertyModel)
            .filter_by(account_id=account_id, status="active")
            .count()
        )