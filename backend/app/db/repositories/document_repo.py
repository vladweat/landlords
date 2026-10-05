"""Репозиторий документов."""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models.document_model import DocumentModel
from app.domain.entities import DocumentEntity
from app.domain.interfaces import IDocumentRepository


class DocumentRepository(IDocumentRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: DocumentEntity) -> DocumentEntity:
        model = DocumentModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def get_by_contract(self, contract_id: UUID, account_id: UUID) -> list[DocumentEntity]:
        models = (
            self.session.query(DocumentModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .order_by(DocumentModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def get_by_property(self, property_id: UUID, account_id: UUID) -> list[DocumentEntity]:
        models = (
            self.session.query(DocumentModel)
            .filter_by(property_id=property_id, account_id=account_id)
            .order_by(DocumentModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def get_by_id(self, doc_id: UUID, account_id: UUID) -> DocumentEntity | None:
        model = (
            self.session.query(DocumentModel)
            .filter_by(id=doc_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def delete(self, doc_id: UUID, account_id: UUID) -> bool:
        model = (
            self.session.query(DocumentModel)
            .filter_by(id=doc_id, account_id=account_id)
            .first()
        )
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def sum_size_bytes(self, account_id: UUID) -> int:
        """Суммарный размер документов аккаунта в байтах."""
        total = (
            self.session.query(func.coalesce(func.sum(DocumentModel.size_bytes), 0))
            .filter_by(account_id=account_id)
            .scalar()
        )
        return int(total or 0)

    def list_by_account(self, account_id: UUID) -> list[DocumentEntity]:
        """Все документы аккаунта."""
        models = (
            self.session.query(DocumentModel)
            .filter_by(account_id=account_id)
            .order_by(DocumentModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]
