"""Реализация репозитория шаблонов договоров."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.contract_template_model import ContractTemplateModel
from app.domain.entities import ContractTemplateEntity
from app.domain.interfaces import IContractTemplateRepository


class ContractTemplateRepository(IContractTemplateRepository):
    """Реализация репозитория шаблонов на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_account(self, account_id: UUID) -> list[ContractTemplateEntity]:
        models = (
            self.session.query(ContractTemplateModel)
            .filter_by(account_id=account_id)
            .order_by(ContractTemplateModel.name.asc())
            .all()
        )
        return [m.to_entity() for m in models]

    def get_by_id(
        self, template_id: UUID, account_id: UUID
    ) -> ContractTemplateEntity | None:
        model = (
            self.session.query(ContractTemplateModel)
            .filter_by(id=template_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def create(self, entity: ContractTemplateEntity) -> ContractTemplateEntity:
        model = ContractTemplateModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: ContractTemplateEntity) -> ContractTemplateEntity:
        model = (
            self.session.query(ContractTemplateModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("ContractTemplate not found")
        model.name = entity.name
        model.title = entity.title
        model.body = entity.body
        model.property_type = entity.property_type
        model.is_default = entity.is_default
        self.session.flush()
        return model.to_entity()

    def delete(self, template_id: UUID, account_id: UUID) -> bool:
        model = (
            self.session.query(ContractTemplateModel)
            .filter_by(id=template_id, account_id=account_id)
            .first()
        )
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def clear_defaults(self, account_id: UUID, property_type: str | None) -> None:
        query = self.session.query(ContractTemplateModel).filter_by(
            account_id=account_id, is_default=True
        )
        if property_type is None:
            query = query.filter(ContractTemplateModel.property_type.is_(None))
        else:
            query = query.filter_by(property_type=property_type)
        query.update({"is_default": False}, synchronize_session=False)
        self.session.flush()
