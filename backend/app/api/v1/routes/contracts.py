"""Маршруты для контрактов."""

from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.deps import get_current_account_id, get_current_user_id, get_contract_service, get_ledger_service, get_pdf_service, get_contract_event_repo
from app.api.v1.schemas.contract_schema import (
    ContractCreateRequest,
    ContractListResponse,
    ContractResponse,
    ContractSingleResponse,
    ContractUpdateRequest,
    ContractLedgerResponse,
    LedgerResponse,
)
from app.services.contract_service import ContractService
from app.api.responses import success_response, success_list_response

from app.api.deps import get_current_account_id, get_ledger_service
from app.services.ledger_service import LedgerService
from app.api.pagination import PaginationParams
from app.api.deps import get_contract_event_repo
from app.api.v1.schemas.contract_event_schema import ContractEventResponse, CreateNoteRequest
from app.services.dto.contract_event_dto import CreateNoteDTO
from app.db.repositories.contract_event_repo import ContractEventRepository
from app.domain.entities import ContractEventEntity

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
    service: ContractService = Depends(get_contract_service),
) -> dict:
    """Обновить контракт."""
    dto = service.update_contract(contract_id, account_id, body)
    return {
        "status": "success",
        "data": ContractResponse.model_validate(dto),
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
    from worker import celery_app

    result = celery_app.send_task(
        "app.tasks.charge_tasks.generate_charges_for_contract",
        args=[str(account_id), str(contract_id)],
    )
    return {"status": "success", "data": {"task_id": result.id}}

from fastapi.responses import Response

from app.api.deps import get_pdf_service
from app.services.pdf_service import PdfService


@router.get("/{contract_id}/document")
def get_contract_document(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    service: PdfService = Depends(get_pdf_service),
) -> dict:
    """Сгенерировать и сохранить PDF, вернуть URL."""
    doc = service.generate_and_save(contract_id, account_id)
    url = f"/documents/{account_id}/{contract_id}/{doc.filename}"
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
    return Response(
        content=doc.file_data,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={doc.filename}"},
    )
    
@router.get("/{contract_id}/events")
def list_contract_events(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    pagination: PaginationParams = Depends(),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
) -> dict:
    """Список событий контракта."""
    result = event_repo.list_by_contract(contract_id, account_id, pagination.page, pagination.per_page)
    items = [ContractEventResponse.model_validate(e) for e in result.items]
    return {"status": "success", "data": {"items": items, "total": result.total, "page": result.page, "per_page": result.per_page, "pages": result.pages}}


@router.post("/{contract_id}/events")
def create_contract_note(
    contract_id: UUID,
    body: CreateNoteRequest,
    account_id: UUID = Depends(get_current_account_id),
    user_id: UUID = Depends(get_current_user_id),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
) -> dict:
    """Добавить заметку."""
    entity = ContractEventEntity(
        id=uuid4(), account_id=account_id, contract_id=contract_id,
        event_type="note", title=body.title, description=body.description,
        created_by=user_id,
    )
    created = event_repo.create(entity)
    return {"status": "success", "data": ContractEventResponse.model_validate(created).model_dump()}

# В app/api/v1/routes/contracts.py добавить:

from sqlalchemy.orm import Session
from app.db.session import get_db_session


@router.post("/{contract_id}/refresh-status")
def refresh_contract_status(
    contract_id: UUID,
    account_id: UUID = Depends(get_current_account_id),
    session: Session = Depends(get_db_session),
) -> dict:
    """Принудительно пересчитать статус контракта."""
    from app.services.payment_service import _check_and_update_contract_status
    from app.db.repositories.contract_repo import ContractRepository
    from app.db.repositories.payment_repo import PaymentRepository
    from app.db.repositories.rent_charge_repo import RentChargeRepository
    from app.core.exceptions import NotFoundError

    contract_repo = ContractRepository(session)
    charge_repo = RentChargeRepository(session)
    payment_repo = PaymentRepository(session)

    contract = contract_repo.get_by_id(contract_id, account_id)
    if not contract:
        raise NotFoundError(f"Contract {contract_id} not found")

    _check_and_update_contract_status(
        charge_repo, payment_repo, contract_repo,
        contract_id, account_id,
    )
    session.commit()

    contract = contract_repo.get_by_id(contract_id, account_id)
    return {
        "status": "success",
        "data": {
            "id": str(contract.id),
            "status": contract.status,
        },
    }