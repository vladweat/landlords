"""Сервис событий контракта."""

from uuid import UUID, uuid4

from app.core.exceptions import NotFoundError
from app.domain.entities import ContractEventEntity
from app.domain.interfaces import IContractEventRepository, IContractRepository
from app.domain.pagination import PaginatedResult
from app.services.dto.contract_event_dto import ContractEventDTO, CreateNoteDTO


class ContractEventService:
    """Сервис управления событиями контракта."""

    def __init__(
        self,
        event_repo: IContractEventRepository,
        contract_repo: IContractRepository,
    ) -> None:
        self.event_repo = event_repo
        self.contract_repo = contract_repo

    def list_events(
        self, contract_id: UUID, account_id: UUID, page: int = 1, per_page: int = 20,
    ) -> PaginatedResult:
        if not self.contract_repo.get_by_id(contract_id, account_id):
            raise NotFoundError(f"Contract with id={contract_id} not found")
        return self.event_repo.list_by_contract(contract_id, account_id, page, per_page)

    def create_note(
        self,
        contract_id: UUID,
        account_id: UUID,
        user_id: UUID,
        dto: CreateNoteDTO,
    ) -> ContractEventDTO:
        if not self.contract_repo.get_by_id(contract_id, account_id):
            raise NotFoundError(f"Contract with id={contract_id} not found")
        entity = ContractEventEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            event_type="note",
            title=dto.title,
            description=dto.description,
            created_by=user_id,
        )
        created = self.event_repo.create(entity)
        return ContractEventDTO.model_validate(created)
