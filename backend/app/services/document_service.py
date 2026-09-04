"""Сервис загружаемых вложений к договору и объекту."""

import os
import re
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import DocumentEntity
from app.domain.interfaces import (
    IContractRepository,
    IDocumentRepository,
    IPropertyRepository,
)

STORAGE_DIR = "/app/storage/documents"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
ALLOWED_UPLOAD_CATEGORIES = {"passport", "act", "photo", "other"}
MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def document_download_url(doc_id: UUID) -> str:
    """Публичный API-путь для скачивания документа."""
    return f"/api/v1/documents/{doc_id}"


def serialize_document(doc: DocumentEntity) -> dict:
    """Словарь документа для API-ответа."""
    return {
        "id": str(doc.id),
        "contract_id": str(doc.contract_id) if doc.contract_id else None,
        "property_id": str(doc.property_id) if doc.property_id else None,
        "filename": doc.filename,
        "title": doc.title or doc.filename,
        "category": doc.category,
        "mime_type": doc.mime_type,
        "size_bytes": doc.size_bytes,
        "source": doc.source,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "url": document_download_url(doc.id),
    }


class DocumentService:
    """Загрузка, список и удаление вложений."""

    def __init__(
        self,
        document_repo: IDocumentRepository,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
    ) -> None:
        self.document_repo = document_repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo

    def list_by_contract(self, contract_id: UUID, account_id: UUID) -> list[DocumentEntity]:
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        return self.document_repo.get_by_contract(contract_id, account_id)

    def list_by_property(self, property_id: UUID, account_id: UUID) -> list[DocumentEntity]:
        prop = self.property_repo.get_by_id(property_id, account_id)
        if not prop:
            raise NotFoundError(f"Property with id={property_id} not found")
        return self.document_repo.get_by_property(property_id, account_id)

    def get_document(self, doc_id: UUID, account_id: UUID) -> DocumentEntity:
        doc = self.document_repo.get_by_id(doc_id, account_id)
        if not doc:
            raise NotFoundError(f"Document {doc_id} not found")
        return doc

    async def upload_for_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        file: UploadFile,
        title: str | None = None,
        category: str = "other",
    ) -> DocumentEntity:
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        return await self._upload(
            account_id=account_id,
            file=file,
            title=title,
            category=category,
            contract_id=contract_id,
            property_id=None,
        )

    async def upload_for_property(
        self,
        property_id: UUID,
        account_id: UUID,
        file: UploadFile,
        title: str | None = None,
        category: str = "other",
    ) -> DocumentEntity:
        prop = self.property_repo.get_by_id(property_id, account_id)
        if not prop:
            raise NotFoundError(f"Property with id={property_id} not found")
        return await self._upload(
            account_id=account_id,
            file=file,
            title=title,
            category=category,
            contract_id=None,
            property_id=property_id,
        )

    def delete(self, doc_id: UUID, account_id: UUID) -> None:
        doc = self.get_document(doc_id, account_id)
        deleted = self.document_repo.delete(doc_id, account_id)
        if not deleted:
            raise NotFoundError(f"Document {doc_id} not found")
        if doc.file_path and os.path.isfile(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError:
                pass

    async def _upload(
        self,
        account_id: UUID,
        file: UploadFile,
        title: str | None,
        category: str,
        contract_id: UUID | None,
        property_id: UUID | None,
    ) -> DocumentEntity:
        if category not in ALLOWED_UPLOAD_CATEGORIES:
            raise ValidationError(
                f"Недопустимая категория. Допустимы: {', '.join(sorted(ALLOWED_UPLOAD_CATEGORIES))}"
            )

        original_name = file.filename or "file"
        safe_name = self._safe_filename(original_name)
        mime_type = self._resolve_mime(file.content_type, safe_name)
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                "Допустимы только PDF, JPEG, PNG и WebP"
            )

        content = await file.read()
        size = len(content)
        if size == 0:
            raise ValidationError("Пустой файл")
        if size > MAX_UPLOAD_BYTES:
            raise ValidationError("Размер файла не должен превышать 15 МБ")

        if contract_id is not None:
            dir_path = os.path.join(STORAGE_DIR, str(account_id), str(contract_id))
        else:
            dir_path = os.path.join(
                STORAGE_DIR, str(account_id), "properties", str(property_id)
            )
        os.makedirs(dir_path, exist_ok=True)

        stored_name = f"{uuid4().hex[:12]}_{safe_name}"
        file_path = os.path.join(dir_path, stored_name)
        with open(file_path, "wb") as f:
            f.write(content)

        doc = DocumentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            property_id=property_id,
            filename=stored_name,
            file_path=file_path,
            title=title.strip() if title and title.strip() else original_name,
            category=category,
            mime_type=mime_type,
            size_bytes=size,
            source="uploaded",
        )
        return self.document_repo.create(doc)

    @staticmethod
    def _safe_filename(name: str) -> str:
        base = os.path.basename(name).strip() or "file"
        base = re.sub(r"[^\w.\-а-яА-ЯёЁ ]+", "_", base, flags=re.UNICODE)
        return base[:180]

    @staticmethod
    def _resolve_mime(content_type: str | None, filename: str) -> str:
        if content_type and content_type in ALLOWED_MIME_TYPES:
            return content_type
        ext = os.path.splitext(filename)[1].lower()
        return MIME_BY_EXT.get(ext, content_type or "application/octet-stream")
