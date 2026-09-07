"""Реализация репозитория квитанций."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.invoice_model import InvoiceModel
from app.domain.entities import InvoiceEntity
from app.domain.interfaces import IInvoiceRepository


class InvoiceRepository(IInvoiceRepository):
    """Репозиторий квитанций на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        model = InvoiceModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: InvoiceEntity) -> InvoiceEntity:
        model = self.session.query(InvoiceModel).filter_by(
            id=entity.id, account_id=entity.account_id
        ).first()
        if not model:
            raise ValueError("Invoice not found")
        model.document_id = entity.document_id
        model.public_token = entity.public_token
        self.session.flush()
        return model.to_entity()

    def get_by_charge(self, charge_id: UUID, account_id: UUID) -> InvoiceEntity | None:
        model = (
            self.session.query(InvoiceModel)
            .filter_by(charge_id=charge_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def get_by_token(self, public_token: str) -> InvoiceEntity | None:
        model = (
            self.session.query(InvoiceModel)
            .filter_by(public_token=public_token)
            .first()
        )
        return model.to_entity() if model else None

    def get_by_id(self, invoice_id: UUID, account_id: UUID) -> InvoiceEntity | None:
        model = (
            self.session.query(InvoiceModel)
            .filter_by(id=invoice_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None
