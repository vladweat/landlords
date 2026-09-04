"""Маршруты для контрактов."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import (
    get_contract_event_service,
    get_contract_service,
    get_current_account_id,
    get_current_user_id,
    get_ledger_service,
    get_payment_service,
    get_pdf_service,
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
from app.services.contract_event_service import ContractEventService
from app.services.contract_service import ContractService
from app.services.dto.contract_event_dto import CreateNoteDTO
from app.services.ledger_service import LedgerService
from app.services.payment_service import PaymentService
from app.services.pdf_service import PdfService

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
) -> dict:
    """Распределить неаллоцированный аванс по неоплаченным начислениям."""
    data = service.allocate_advance(contract_id, account_id)
    return {"status": "success", "data": data}


@router.get("/{contract_id}/document")
def get_contract_document(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PdfService = Depends(get_pdf_service),
) -> dict:
    """Сгенерировать и сохранить PDF, вернуть защищённый URL через API."""
    doc = service.generate_and_save(contract_id, account_id)
    # Возвращаем ссылку на API-эндоинт, который отдаёт документ с авторизацией.
    url = f"/api/v1/contracts/documents/{doc.id}"
    return {"status": "success", "data": {"url": url, "filename": doc.filename}}


@router.get("/{contract_id}/documents")
def list_contract_documents(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PdfService = Depends(get_pdf_service),
) -> dict:
    """Список сохранённых документов."""
    docs = service.get_documents(contract_id, account_id)
    return {
        "status": "success",
        "data": [
            {"id": str(d.id), "filename": d.filename, "created_at": d.created_at.isoformat()}
            for d in docs
        ],
    }


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PdfService = Depends(get_pdf_service),
) -> Response:
    """Скачать сохранённый документ по ID."""
    doc = service.get_document(doc_id, account_id)
    with open(doc.file_path, "rb") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={doc.filename}"},
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
