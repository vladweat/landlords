"""Репозиторий событий контракта."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.api.pagination import paginate
from app.domain.pagination import PaginatedResult
from app.db.models.contract_event_model import ContractEventModel
from app.domain.entities import ContractEventEntity
from app.domain.interfaces import IContractEventRepository


class ContractEventRepository(IContractEventRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: ContractEventEntity) -> ContractEventEntity:
        model = ContractEventModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def list_by_contract(
        self, contract_id: UUID, account_id: UUID, page: int = 1, per_page: int = 20
    ) -> PaginatedResult:
        query = (
            self.session.query(ContractEventModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .order_by(ContractEventModel.created_at.desc())
        )
        return paginate(query, page, per_page)