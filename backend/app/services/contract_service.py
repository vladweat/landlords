"""Сервис управления контрактами."""

from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import ContractEntity, ContractEventEntity
from app.domain.interfaces import (
    IContractEventRepository,
    IContractRepository,
    IPaymentRepository,
    IRentChargeRepository,
)
from app.domain.rules import (
    compute_ledger,
    validate_contract_dates,
    validate_payment_day,
    validate_status_transition,
)
from app.services.audit_log_service import AuditService
from app.services.contract_status import check_and_update_contract_status
from app.services.dto.contract_dto import (
    ContractCreateDTO,
    ContractDTO,
    ContractUpdateDTO,
)
from app.services.dto.dashboard_dto import LedgerDTO


def _run_rule(rule, *args, **kwargs) -> None:
    """Выполнить доменное правило, обернув ValueError в ValidationError."""
    try:
        rule(*args, **kwargs)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


class ContractService:
    def __init__(
        self,
        repo: IContractRepository,
        charge_repo: IRentChargeRepository | None = None,
        payment_repo: IPaymentRepository | None = None,
        event_repo: IContractEventRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repo = repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.event_repo = event_repo
        self.audit_service = audit_service

    def list_contracts(
        self, account_id: UUID, page: int = 1, per_page: int = 20,
        overdue_only: bool = False, search: str | None = None,
        status: str | None = None,
    ) -> dict:
        return self.repo.list_by_account(
            account_id, page=page, per_page=per_page,
            overdue_only=overdue_only, search=search, status=status,
        )

    def get_contract(self, contract_id: UUID, account_id: UUID) -> ContractDTO:
        """Получить контракт по ID."""
        entity = self.repo.get_by_id(contract_id, account_id)
        if not entity:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        return ContractDTO.model_validate(entity)

    def create_contract(
        self, account_id: UUID, dto: ContractCreateDTO
    ) -> ContractDTO:
        """Создать контракт."""
        _run_rule(validate_contract_dates, dto.start_date, dto.end_date)
        _run_rule(validate_payment_day, dto.payment_day)

        existing = self.repo.get_active_by_property(dto.property_id, account_id)
        if existing:
            raise ConflictError(
                f"Property {dto.property_id} already has an active contract"
            )

        entity = ContractEntity(
            id=uuid4(),
            account_id=account_id,
            property_id=dto.property_id,
            tenant_id=dto.tenant_id,
            start_date=dto.start_date,
            end_date=dto.end_date,
            rent_amount=dto.rent_amount,
            currency=dto.currency,
            billing_period="monthly",
            payment_day=dto.payment_day,
            deposit_amount=dto.deposit_amount,
            auto_generate_charges=dto.auto_generate_charges,
            status="draft",
        )
        created = self.repo.create(entity)
        return ContractDTO.model_validate(created)

    def update_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        dto: ContractUpdateDTO,
        user_id: UUID | None = None,
    ) -> ContractDTO:
        """Обновить контракт."""
        entity = self.repo.get_by_id(contract_id, account_id)
        if not entity:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        old_status = entity.status

        if dto.status and dto.status != entity.status:
            _run_rule(validate_status_transition, entity.status, dto.status)

        if dto.status and dto.status != old_status and self.event_repo:
            self.event_repo.create(ContractEventEntity(
                id=uuid4(), account_id=account_id, contract_id=contract_id,
                event_type="status_change",
                title=f"Статус изменён: {old_status} → {dto.status}",
                event_metadata={"old_status": old_status, "new_status": dto.status},
            ))

        if dto.status == "active" and entity.status != "active":
            existing = self.repo.get_active_by_property(entity.property_id, account_id)
            if existing and existing.id != entity.id:
                raise ConflictError(
                    f"Property {entity.property_id} already has an active contract"
                )

        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        if dto.start_date or dto.end_date:
            _run_rule(validate_contract_dates, entity.start_date, entity.end_date)
        if dto.payment_day is not None:
            _run_rule(validate_payment_day, entity.payment_day)

        updated = self.repo.update(entity)

        if dto.status and dto.status != old_status and self.audit_service and user_id:
            self.audit_service.log(
                user_id=user_id,
                action="status_change",
                entity_type="contract",
                entity_id=contract_id,
                old_data={"status": old_status},
                new_data={"status": dto.status},
            )

        if (
            dto.status == "active"
            and old_status != "active"
            and entity.auto_generate_charges
            and self.charge_repo
        ):
            from app.celery_app import celery_app
            celery_app.send_task(
                "app.tasks.charge_tasks.generate_charges_for_contract",
                args=[str(account_id), str(contract_id)],
            )

        return ContractDTO.model_validate(updated)

    def delete_contract(self, contract_id: UUID, account_id: UUID) -> None:
        """Удалить контракт."""
        entity = self.repo.get_by_id(contract_id, account_id)
        if not entity:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        self.repo.delete(contract_id, account_id)

    def refresh_contract_status(self, contract_id: UUID, account_id: UUID) -> ContractDTO:
        """Принудительно пересчитать статус контракта."""
        contract = self.repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        if not self.charge_repo or not self.payment_repo:
            raise ValidationError("Charge and payment repositories are required")

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.repo,
            contract_id, account_id,
        )
        updated = self.repo.get_by_id(contract_id, account_id)
        return ContractDTO.model_validate(updated)

    def get_ledger(self, contract_id: UUID, account_id: UUID) -> LedgerDTO:
        """Получить финансовое состояние контракта."""
        contract = self.repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        if not self.charge_repo or not self.payment_repo:
            raise ValueError("Ledger requires charge_repo and payment_repo")

        charges = self.charge_repo.list_by_contract(contract_id, account_id)
        total_paid = self.payment_repo.get_total_paid_for_contract(
            contract_id, account_id
        )

        ledger = compute_ledger(charges, total_paid)
        return LedgerDTO(**ledger)
