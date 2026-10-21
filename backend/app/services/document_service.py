"""Сервис загружаемых вложений к договору и объекту."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import UploadFile

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import DocumentEntity
from app.domain.interfaces import (
    IContractRepository,
    IDocumentRepository,
    IPropertyRepository,
)

if TYPE_CHECKING:
    from app.services.plan_limit_service import PlanLimitService

STORAGE_DIR = os.getenv("DOCUMENTS_STORAGE_DIR", "/app/storage/documents")
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


def document_file_path(doc: DocumentEntity, account_id: UUID) -> Path:
    """Разрешить путь только внутри каталога хранения текущего аккаунта."""
    try:
        root = Path(STORAGE_DIR).resolve(strict=True)
        path = Path(doc.file_path).resolve(strict=True)
        relative = path.relative_to(root)
    except (OSError, ValueError):
        raise NotFoundError("Document file not found") from None
    if (
        not path.is_file()
        or not relative.parts
        or relative.parts[0] != str(account_id)
    ):
        raise NotFoundError("Document file not found")
    return path


def document_attachment_headers(filename: str) -> dict[str, str]:
    """Сформировать безопасные HTTP-заголовки для скачивания файла."""
    name = os.path.basename(filename).replace("\r", "").replace("\n", "") or "document"
    fallback = re.sub(r"[^A-Za-z0-9._-]", "_", name) or "document"
    return {
        "Content-Disposition": (
            f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(name, safe="")}'
        ),
        "X-Content-Type-Options": "nosniff",
    }


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
        plan_limit_service: PlanLimitService | None = None,
    ) -> None:
        self.document_repo = document_repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.plan_limit_service = plan_limit_service

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
        self.get_document(doc_id, account_id)
        deleted = self.document_repo.delete(doc_id, account_id)
        if not deleted:
            raise NotFoundError(f"Document {doc_id} not found")
        # Keep the file until the request transaction commits. If the later DB
        # commit fails, the still-present file keeps the existing row downloadable.
        # Orphan files are removed by the documented reconciliation command.

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
        content = await file.read(MAX_UPLOAD_BYTES + 1)
        size = len(content)
        if size == 0:
            raise ValidationError("Пустой файл")
        if size > MAX_UPLOAD_BYTES:
            raise ValidationError("Размер файла не должен превышать 15 МБ")
        mime_type = self._detect_mime(content)
        extension_mime = MIME_BY_EXT.get(os.path.splitext(safe_name)[1].lower())
        declared_mime = file.content_type
        if (
            mime_type not in ALLOWED_MIME_TYPES
            or extension_mime != mime_type
            or (
                declared_mime
                and declared_mime != "application/octet-stream"
                and declared_mime != mime_type
            )
        ):
            raise ValidationError("Содержимое файла не соответствует PDF, JPEG, PNG или WebP")
        if self.plan_limit_service:
            self.plan_limit_service.assert_can_upload(account_id, size)

        if contract_id is not None:
            dir_path = os.path.join(STORAGE_DIR, str(account_id), str(contract_id))
        else:
            dir_path = os.path.join(
                STORAGE_DIR, str(account_id), "properties", str(property_id)
            )
        os.makedirs(dir_path, exist_ok=True)

        stored_name = f"{uuid4().hex[:12]}_{safe_name}"
        file_path = os.path.join(dir_path, stored_name)
        temp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=dir_path, prefix=".upload-", delete=False
            ) as stream:
                temp_path = stream.name
                stream.write(content)
            os.replace(temp_path, file_path)
            temp_path = None
        except OSError:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
            raise

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
        try:
            return self.document_repo.create(doc)
        except Exception:
            try:
                os.remove(file_path)
            except OSError:
                pass
            raise

    @staticmethod
    def _safe_filename(name: str) -> str:
        base = os.path.basename(name).strip() or "file"
        base = re.sub(r"[^\w.\-а-яА-ЯёЁ ]+", "_", base, flags=re.UNICODE)
        return base[:180]

    @staticmethod
    def _detect_mime(content: bytes) -> str:
        """Определить поддерживаемый тип по сигнатуре, а не заголовку клиента."""
        if content.startswith(b"%PDF-"):
            return "application/pdf"
        if content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "image/webp"
        return "application/octet-stream"
