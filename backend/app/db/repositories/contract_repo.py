"""Реализация репозитория контрактов."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.contract_model import ContractModel
from app.domain.entities import ContractEntity
from app.domain.interfaces import IContractRepository
from app.api.pagination import PaginatedResult, paginate

class ContractRepository(IContractRepository):
    """Реализация репозитория контрактов на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, contract_id: UUID, account_id: UUID) -> ContractEntity | None:
        """Получить контракт по ID с проверкой account_id."""
        model = (
            self.session.query(ContractModel)
            .filter_by(id=contract_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def list_by_account(
        self, account_id: UUID, page: int = 1, per_page: int = 20,
        overdue_only: bool = False, search: str | None = None,
        status: str | None = None,
    ) -> PaginatedResult:
        query = (
            self.session.query(ContractModel)
            .filter_by(account_id=account_id)
            .order_by(ContractModel.created_at.desc())
        )
        if overdue_only:
            query = query.filter_by(status="overdue")
        if status:
            query = query.filter_by(status=status)
        if search:
            from sqlalchemy import func
            from app.db.models.tenant_model import TenantModel
            from app.db.models.property_model import PropertyModel

            query = query.join(TenantModel, ContractModel.tenant_id == TenantModel.id) \
                        .join(PropertyModel, ContractModel.property_id == PropertyModel.id) \
                        .filter(
                            (TenantModel.full_name.ilike(f"%{search}%")) |
                            (func.concat(
                                PropertyModel.city, ', ул. ', PropertyModel.street,
                                ', д. ', PropertyModel.house
                            ).ilike(f"%{search}%"))
                        )

        return paginate(query, page, per_page)

    def get_active_by_property(
        self, property_id: UUID, account_id: UUID
    ) -> ContractEntity | None:
        """Получить активный контракт по объекту недвижимости."""
        model = (
            self.session.query(ContractModel)
            .filter_by(
                property_id=property_id,
                account_id=account_id,
                status="active",
            )
            .first()
        )
        return model.to_entity() if model else None

    def create(self, entity: ContractEntity) -> ContractEntity:
        """Создать контракт."""
        model = ContractModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: ContractEntity) -> ContractEntity:
        """Обновить контракт."""
        model = (
            self.session.query(ContractModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Contract not found")
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.rent_amount = entity.rent_amount
        model.currency = entity.currency
        model.billing_period = entity.billing_period
        model.payment_day = entity.payment_day
        model.deposit_amount = entity.deposit_amount
        model.auto_generate_charges = entity.auto_generate_charges
        model.status = entity.status
        model.termination_reason = entity.termination_reason
        self.session.flush()
        return model.to_entity()

    def delete(self, contract_id: UUID, account_id: UUID) -> None:
        """Удалить контракт."""
        self.session.query(ContractModel).filter_by(
            id=contract_id, account_id=account_id
        ).delete()
        self.session.flush()
        
    def count_active(self, account_id: UUID) -> int:
        """Количество активных контрактов."""
        return (
            self.session.query(ContractModel)
            .filter(
                ContractModel.account_id == account_id,
                ContractModel.status.in_(["active", "overdue"]),
            )
            .count()
        )
            
    def get_active_for_property(
        self, property_id: UUID, account_id: UUID
    ) -> ContractEntity | None:
        """Получить активный (active/overdue) контракт для объекта."""
        model = (
            self.session.query(ContractModel)
            .filter(
                ContractModel.property_id == property_id,
                ContractModel.account_id == account_id,
                ContractModel.status.in_(["active", "overdue"]),
            )
            .first()
        )
        return model.to_entity() if model else None
    
    def get_active_for_tenant(
        self, tenant_id: UUID, account_id: UUID
    ) -> list[ContractEntity]:
        """Получить активные контракты арендатора."""
        models = (
            self.session.query(ContractModel)
            .filter(
                ContractModel.tenant_id == tenant_id,
                ContractModel.account_id == account_id,
                ContractModel.status.in_(["active", "overdue"]),
            )
            .all()
        )
        return [m.to_entity() for m in models]