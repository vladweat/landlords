"""Сервис управления контрактами."""

from uuid import UUID, uuid4

from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import ContractEntity
from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository
from app.domain.rules import validate_contract_dates, compute_ledger, validate_status_transition,validate_payment_day
from app.services.dto.contract_dto import (
    ContractCreateDTO,
    ContractDTO,
    ContractUpdateDTO,
)
from app.services.dto.dashboard_dto import LedgerDTO
from sqlalchemy.orm import Session
from app.services.audit_log_service import AuditService


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
        session: Session | None = None,
    ) -> None:
        self.repo = repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.session = session

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
        # Валидация дат
        _run_rule(validate_contract_dates, dto.start_date, dto.end_date)
        _run_rule(validate_payment_day, dto.payment_day)

        # Проверка: нет ли активного контракта на этот объект
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
            billing_period="monthly",  # фиксировано
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

        # Проверка перехода статуса
        if dto.status and dto.status != entity.status:
            _run_rule(validate_status_transition, entity.status, dto.status)

        if dto.status and dto.status != old_status and self.session:
            from app.db.repositories.contract_event_repo import ContractEventRepository
            from app.domain.entities import ContractEventEntity
            event_repo = ContractEventRepository(self.session)
            event_repo.create(ContractEventEntity(
                id=uuid4(), account_id=account_id, contract_id=contract_id,
                event_type="status_change",
                title=f"Статус изменён: {old_status} → {dto.status}",
                event_metadata={"old_status": old_status, "new_status": dto.status},
            ))

        # Проверка "1 активный на Property"
        if dto.status == "active" and entity.status != "active":
            existing = self.repo.get_active_by_property(entity.property_id, account_id)
            if existing and existing.id != entity.id:
                raise ConflictError(
                    f"Property {entity.property_id} already has an active contract"
                )

        # Обновляем поля
        update_data = dto.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(entity, field):
                setattr(entity, field, value)

        # Валидация
        if dto.start_date or dto.end_date:
            _run_rule(validate_contract_dates, entity.start_date, entity.end_date)
        if dto.payment_day is not None:
            _run_rule(validate_payment_day, entity.payment_day)

        updated = self.repo.update(entity)

        # Аудит смены статуса
        if dto.status and dto.status != old_status and self.session and user_id:
            audit = AuditService(self.session)
            audit.log(
                user_id=user_id,
                action="status_change",
                entity_type="contract",
                entity_id=contract_id,
                old_data={"status": old_status},
                new_data={"status": dto.status},
            )

        # Автогенерация начислений при активации
        if (
            dto.status == "active"
            and old_status != "active"
            and entity.auto_generate_charges
            and self.charge_repo
        ):
            from worker import celery_app
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