"""Маршруты для объектов недвижимости."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.deps import (
    get_current_account_id,
    get_document_service,
    get_property_service,
    get_roi_service,
    require_permissions,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.api.v1.schemas.property_schema import (
    PropertyCreateRequest,
    PropertyListResponse,
    PropertyResponse,
    PropertySingleResponse,
    PropertyUpdateRequest,
)
from app.services.property_service import PropertyService
from app.services.roi_service import RoiService
from app.services.document_service import DocumentService, serialize_document

from app.api.responses import success_response, success_list_response
from app.api.pagination import PaginationParams
from app.api.v1.schemas.common import PaginatedData

router = APIRouter(prefix="/v1/properties", tags=["Properties"])


@router.get("")
def list_properties(
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyService = Depends(get_property_service),
    pagination: PaginationParams = Depends(),
    search: str | None = None,
    type: str | None = None,
    roi_service: RoiService = Depends(get_roi_service),
) -> dict:
    """Получить список объектов недвижимости."""
    result = service.list_properties(
        account_id,
        page=pagination.page,
        per_page=pagination.per_page,
        search=search,
        property_type=type,
    )
    items = []
    roi_batch = roi_service.calculate_roi_batch(account_id)
    for e in result.items:
        item = PropertyResponse.model_validate(e).model_dump()
        parts = [f"г. {e.city}", f"ул. {e.street}", f"д. {e.house}"]
        if getattr(e, 'building', None):
            parts.append(f"корп. {e.building}")
        if getattr(e, 'apartment', None):
            parts.append(f"кв. {e.apartment}")
        item["address"] = ", ".join(parts)
        item["roi"] = roi_batch.get(e.id, {})
        items.append(item)

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
            "pages": result.pages,
        },
    }


@router.get("/{property_id}")
def get_property(
    property_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyService = Depends(get_property_service),
    roi_service: RoiService = Depends(get_roi_service),
) -> dict:
    dto = service.get_property(property_id, account_id)
    roi = roi_service.calculate_roi(property_id, account_id)
    result = PropertyResponse.model_validate(dto).model_dump()
    result["address"] = dto.get_address()
    result["roi"] = roi
    return {"status": "success", "data": result}


@router.post("", response_model=PropertySingleResponse, status_code=201)
def create_property(
    body: PropertyCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyService = Depends(get_property_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PROPERTIES)),
) -> dict:
    """Создать объект недвижимости."""
    dto = service.create_property(account_id, body)
    data = PropertyResponse.model_validate(dto).model_dump()
    data["address"] = dto.get_address()
    return {"status": "success", "data": data}


@router.put("/{property_id}", response_model=PropertySingleResponse)
def update_property(
    property_id: UUID,
    body: PropertyUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyService = Depends(get_property_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PROPERTIES)),
) -> dict:
    """Обновить объект недвижимости."""
    dto = service.update_property(property_id, account_id, body)
    return {
        "status": "success",
        "data": PropertyResponse.model_validate(dto),
    }


@router.delete("/{property_id}", status_code=204)
def delete_property(
    property_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PropertyService = Depends(get_property_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PROPERTIES)),
) -> None:
    """Удалить объект недвижимости."""
    service.delete_property(property_id, account_id)


@router.get("/{property_id}/documents")
def list_property_documents(
    property_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    """Список вложений объекта."""
    docs = service.list_by_property(property_id, account_id)
    return {"status": "success", "data": [serialize_document(d) for d in docs]}


@router.post("/{property_id}/documents")
async def upload_property_document(
    property_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str = Form("other"),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_DOCUMENTS)),
) -> dict:
    """Загрузить вложение к объекту."""
    doc = await service.upload_for_property(
        property_id, account_id, file, title=title, category=category
    )
    return {"status": "success", "data": serialize_document(doc)}

