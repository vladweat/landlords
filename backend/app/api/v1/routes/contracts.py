"""Маршруты для контрактов."""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import (
    get_contract_event_service,
    get_contract_service,
    get_current_account_id,
    get_current_user_id,
    get_document_service,
    get_ledger_service,
    get_payment_service,
    get_pdf_service,
    get_tenant_portal_service,
    require_permissions,
)
from app.api.pagination import PaginationParams
from app.api.v1.schemas.contract_event_schema import ContractEventResponse, CreateNoteRequest
from app.api.v1.schemas.contract_schema import (
    ContractCreateRequest,
    ContractResponse,
    ContractSingleResponse,
    ContractUpdateRequest,
    ContractTerminateRequest,
    ContractRenewRequest,
    ContractLifecycleResponse,
    ContractLifecycleSingleResponse,
    ContractLedgerResponse,
    LedgerResponse,
)
from app.api.v1.schemas.portal_schema import (
    PaymentClaimListResponse,
    PaymentClaimResponse,
    PortalLinkResponse,
    PortalLinkSingleResponse,
)
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission
from app.services.contract_event_service import ContractEventService
from app.services.contract_service import ContractService
from app.services.document_service import DocumentService, serialize_document
from app.services.dto.contract_event_dto import CreateNoteDTO
from app.services.ledger_service import LedgerService
from app.services.payment_service import PaymentService
from app.services.pdf_service import PdfService
from app.services.tenant_portal_service import TenantPortalService

router = APIRouter(prefix="/v1/contracts", tags=["Contracts"])


@router.get("")
def list_contracts(
    account_id: UUID = Depends(get_current_account_id),
    service: ContractService = Depends(get_contract_service),
    pagination: PaginationParams = Depends(),
    overdue_only: bool = False,
    search: str | None = None,
    status: str | None = None,
) -> dict:
    result = service.list_contracts(
        account_id, page=pagination.page, per_page=pagination.per_page,
        overdue_only=overdue_only, search=search, status=status,
    )
    items = [ContractResponse.model_validate(e) for e in result.items]
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


@router.post("", response_model=ContractSingleResponse, status_code=201)
def create_contract(
    body: ContractCreateRequest,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Создать контракт."""
    dto = service.create_contract(account_id, body)
    return {
        "status": "success",
        "data": ContractResponse.model_validate(dto),
    }


@router.get("/{contract_id}", response_model=ContractSingleResponse)
def get_contract(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractService = Depends(get_contract_service),
) -> dict:
    """Получить контракт по ID."""
    dto = service.get_contract(contract_id, account_id)
    return {
        "status": "success",
        "data": ContractResponse.model_validate(dto),
    }


@router.put("/{contract_id}", response_model=ContractSingleResponse)
def update_contract(
    contract_id: UUID,
    body: ContractUpdateRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Обновить контракт."""
    dto = service.update_contract(contract_id, account_id, body, user_id=user_id)
    return {
        "status": "success",
        "data": ContractResponse.model_validate(dto),
    }


@router.post(
    "/{contract_id}/terminate",
    response_model=ContractLifecycleSingleResponse,
)
def terminate_contract(
    contract_id: UUID,
    body: ContractTerminateRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Расторгнуть договор с пересчётом начислений и актом."""
    from app.services.dto.contract_dto import ContractTerminateDTO

    result = service.terminate_contract(
        contract_id,
        account_id,
        ContractTerminateDTO.model_validate(body.model_dump()),
        user_id=user_id,
    )
    return {
        "status": "success",
        "data": ContractLifecycleResponse(
            contract=ContractResponse.model_validate(result.contract),
            charges_deleted=result.charges_deleted,
            charges_updated=result.charges_updated,
            charges_created=result.charges_created,
            document_id=result.document_id,
            document_url=result.document_url,
            document_filename=result.document_filename,
        ),
    }


@router.post(
    "/{contract_id}/renew",
    response_model=ContractLifecycleSingleResponse,
)
def renew_contract(
    contract_id: UUID,
    body: ContractRenewRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Продлить договор с генерацией начислений и допсоглашением."""
    from app.services.dto.contract_dto import ContractRenewDTO

    result = service.renew_contract(
        contract_id,
        account_id,
        ContractRenewDTO.model_validate(body.model_dump()),
        user_id=user_id,
    )
    return {
        "status": "success",
        "data": ContractLifecycleResponse(
            contract=ContractResponse.model_validate(result.contract),
            charges_deleted=result.charges_deleted,
            charges_updated=result.charges_updated,
            charges_created=result.charges_created,
            document_id=result.document_id,
            document_url=result.document_url,
            document_filename=result.document_filename,
        ),
    }


@router.delete("/{contract_id}", status_code=204)
def delete_contract(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> None:
    """Удалить контракт."""
    service.delete_contract(contract_id, account_id)


@router.get("/{contract_id}/ledger", response_model=ContractLedgerResponse)
def get_contract_ledger(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: LedgerService = Depends(get_ledger_service),
) -> dict:
    """Получить финансовый отчёт по контракту."""
    ledger = service.get_ledger(contract_id, account_id)
    return {
        "status": "success",
        "data": LedgerResponse.model_validate(ledger.model_dump()),
    }


@router.post("/{contract_id}/generate-charges")
def generate_charges(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CHARGES)),
) -> dict:
    """Сгенерировать начисления для контракта."""
    from app.celery_app import celery_app

    result = celery_app.send_task(
        "app.tasks.charge_tasks.generate_charges_for_contract",
        args=[str(account_id), str(contract_id)],
    )
    return {"status": "success", "data": {"task_id": result.id}}


@router.post("/{contract_id}/allocate-advance")
def allocate_advance(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PaymentService = Depends(get_payment_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_PAYMENTS)),
) -> dict:
    """Распределить неаллоцированный аванс по неоплаченным начислениям."""
    data = service.allocate_advance(contract_id, account_id)
    return {"status": "success", "data": data}


@router.get("/{contract_id}/document")
def get_contract_document(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PdfService = Depends(get_pdf_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_DOCUMENTS)),
    template_id: UUID | None = Query(None),
) -> dict:
    """Сгенерировать и сохранить PDF, вернуть защищённый URL через API."""
    doc = service.generate_and_save(contract_id, account_id, template_id=template_id)
    url = f"/api/v1/documents/{doc.id}"
    return {"status": "success", "data": {"url": url, "filename": doc.filename}}


@router.get("/{contract_id}/documents")
def list_contract_documents(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
) -> dict:
    """Список документов и вложений договора."""
    docs = service.list_by_contract(contract_id, account_id)
    return {"status": "success", "data": [serialize_document(d) for d in docs]}


@router.post("/{contract_id}/documents")
async def upload_contract_document(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
    file: UploadFile = File(...),
    title: str | None = Form(None),
    category: str = Form("other"),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_DOCUMENTS)),
) -> dict:
    """Загрузить вложение к договору."""
    doc = await service.upload_for_contract(
        contract_id, account_id, file, title=title, category=category
    )
    return {"status": "success", "data": serialize_document(doc)}


@router.get("/documents/{doc_id}")
def get_document_legacy(
    doc_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: DocumentService = Depends(get_document_service),
) -> Response:
    """Скачать документ (alias для совместимости)."""
    doc = service.get_document(doc_id, account_id)
    with open(doc.file_path, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type=doc.mime_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'},
    )


@router.get("/{contract_id}/events")
def list_contract_events(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    pagination: PaginationParams = Depends(),
    service: ContractEventService = Depends(get_contract_event_service),
) -> dict:
    """Список событий контракта."""
    result = service.list_events(
        contract_id, account_id, pagination.page, pagination.per_page,
    )
    items = [ContractEventResponse.model_validate(e) for e in result.items]
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


@router.post("/{contract_id}/events")
def create_contract_note(
    contract_id: UUID,
    body: CreateNoteRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    service: ContractEventService = Depends(get_contract_event_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Добавить заметку."""
    dto = CreateNoteDTO.model_validate(body.model_dump())
    created = service.create_note(contract_id, account_id, user_id, dto)
    return {"status": "success", "data": ContractEventResponse.model_validate(created).model_dump()}


@router.post("/{contract_id}/refresh-status")
def refresh_contract_status(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: ContractService = Depends(get_contract_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Принудительно пересчитать статус контракта."""
    contract = service.refresh_contract_status(contract_id, account_id)
    return {
        "status": "success",
        "data": {
            "id": str(contract.id),
            "status": contract.status,
        },
    }


@router.post("/{contract_id}/portal", response_model=PortalLinkSingleResponse)
def ensure_contract_portal(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantPortalService = Depends(get_tenant_portal_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Создать или вернуть magic link портала арендатора."""
    dto = service.ensure_portal(contract_id, account_id)
    return {
        "status": "success",
        "data": PortalLinkResponse.model_validate(dto),
    }


@router.post("/{contract_id}/portal/rotate", response_model=PortalLinkSingleResponse)
def rotate_contract_portal(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: TenantPortalService = Depends(get_tenant_portal_service),
    _: MembershipEntity = Depends(require_permissions(Permission.WRITE_CONTRACTS)),
) -> dict:
    """Перевыпустить токен портала (старая ссылка перестаёт работать)."""
    dto = service.rotate_portal(contract_id, account_id)
    return {
        "status": "success",
        "data": PortalLinkResponse.model_validate(dto),
    }


@router.get("/{contract_id}/claims", response_model=PaymentClaimListResponse)
def list_contract_claims(
    contract_id: UUID,
    status: str | None = Query(None),
    account_id: UUID = Depends(get_current_account_id),
    service: TenantPortalService = Depends(get_tenant_portal_service),
) -> dict:
    """Список заявок «я оплатил» по договору."""
    items = service.list_claims(contract_id, account_id, status=status)
    return {
        "status": "success",
        "data": [PaymentClaimResponse.model_validate(i) for i in items],
    }
