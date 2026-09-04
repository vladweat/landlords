"""Маршруты документов и вложений."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.api.deps import get_current_account_id, get_document_service, require_permissions
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.document_service import DocumentService, serialize_document

router = APIRouter(prefix="/v1/documents", tags=["Documents"])


@router.get("/{doc_id}")
def download_document(
    doc_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    """Скачать документ по ID."""
    doc = service.get_document(doc_id, account_id)
    with open(doc.file_path, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type=doc.mime_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.delete("/{doc_id}")
def delete_document(
    doc_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_DOCUMENTS)),
) -> dict:
    """Удалить вложение (файл + запись)."""
    service.delete(doc_id, account_id)
    return {"status": "success", "data": {"id": str(doc_id)}}
