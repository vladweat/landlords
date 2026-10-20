"""Сервис управления контрактами."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import ContractEntity, ContractEventEntity, RentChargeEntity
from app.domain.interfaces import (
    IContractEventRepository,
    IContractRepository,
    IPaymentRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import (
    compute_charge_status,
    compute_ledger,
    plan_charges_on_renew,
    plan_charges_on_terminate,
    validate_contract_dates,
    validate_payment_day,
    validate_status_transition,
)
from app.services.audit_log_service import AuditService
from app.services.contract_event_labels import (
    format_date_ru,
    format_money,
    status_label,
)
from app.services.contract_status import check_and_update_contract_status
from app.services.payment_allocation import allocate_unlinked_payments
from app.services.dto.contract_dto import (
    ContractCreateDTO,
    ContractDTO,
    ContractLifecycleResultDTO,
    ContractRenewDTO,
    ContractTerminateDTO,
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
        pdf_service=None,
        *,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
    ) -> None:
        self.repo = repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.event_repo = event_repo
        self.audit_service = audit_service
        self.pdf_service = pdf_service

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

        # ID пришли от клиента: перед созданием связи проверяем принадлежность
        # обоих ресурсов аутентифицированному аккаунту.
        if not self.property_repo.get_by_id(dto.property_id, account_id):
            raise NotFoundError(f"Property with id={dto.property_id} not found")
        if not self.tenant_repo.get_by_id(dto.tenant_id, account_id):
            raise NotFoundError(f"Tenant with id={dto.tenant_id} not found")

        entity = ContractEntity(
            id=uuid4(),
            account_id=account_id,
            property_id=dto.property_id,
            tenant_id=dto.tenant_id,
            start_date=dto.start_date,
            end_date=dto.end_date,
            rent_amount=dto.rent_amount,
            currency=dto.currency,
            billing_period=dto.billing_period,
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
                title=(
                    f"Статус изменён: {status_label(old_status)} → "
                    f"{status_label(dto.status)}"
                ),
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

    def terminate_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        dto: ContractTerminateDTO,
        user_id: UUID | None = None,
    ) -> ContractLifecycleResultDTO:
        """Расторгнуть договор: статус, пересчёт начислений, акт."""
        entity = self.repo.get_by_id(contract_id, account_id)
        if not entity:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        if entity.status not in ("draft", "active", "overdue"):
            raise ValidationError(
                f"Cannot terminate contract in status '{entity.status}'"
            )

        if dto.effective_date < entity.start_date:
            raise ValidationError("effective_date cannot be before start_date")
        if dto.effective_date > entity.end_date:
            raise ValidationError("effective_date cannot be after end_date")

        old_status = entity.status
        old_end = entity.end_date
        _run_rule(validate_status_transition, old_status, "terminated")

        deleted_count = 0
        updated_count = 0
        if self.charge_repo and self.payment_repo:
            deleted_count, updated_count = self._recalc_charges_on_terminate(
                contract_id, account_id, dto.effective_date
            )

        entity.status = "terminated"
        entity.termination_reason = dto.termination_reason
        if dto.effective_date < entity.end_date:
            entity.end_date = dto.effective_date

        updated = self.repo.update(entity)

        if self.event_repo:
            reason = (dto.termination_reason or "").strip()
            description = f"Дата расторжения: {format_date_ru(dto.effective_date)}"
            if reason:
                description = f"{description}\n{reason}"
            self.event_repo.create(ContractEventEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract_id,
                event_type="termination",
                title="Договор расторгнут",
                description=description,
                event_metadata={
                    "old_status": old_status,
                    "effective_date": dto.effective_date.isoformat(),
                    "charges_deleted": deleted_count,
                    "charges_updated": updated_count,
                },
            ))

        if self.audit_service and user_id:
            self.audit_service.log(
                user_id=user_id,
                action="terminate",
                entity_type="contract",
                entity_id=contract_id,
                old_data={"status": old_status, "end_date": str(old_end)},
                new_data={
                    "status": "terminated",
                    "effective_date": dto.effective_date.isoformat(),
                    "termination_reason": dto.termination_reason,
                },
            )

        doc_id = None
        doc_url = None
        doc_filename = None
        if dto.generate_act and self.pdf_service:
            doc = self.pdf_service.generate_termination_act(
                contract_id, account_id, dto.effective_date, dto.termination_reason
            )
            doc_id = doc.id
            doc_filename = doc.filename
            doc_url = f"/api/v1/documents/{doc.id}"

        return ContractLifecycleResultDTO(
            contract=ContractDTO.model_validate(updated),
            charges_deleted=deleted_count,
            charges_updated=updated_count,
            document_id=doc_id,
            document_url=doc_url,
            document_filename=doc_filename,
        )

    def renew_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        dto: ContractRenewDTO,
        user_id: UUID | None = None,
    ) -> ContractLifecycleResultDTO:
        """Продлить договор: новая дата окончания, начисления, допсоглашение."""
        entity = self.repo.get_by_id(contract_id, account_id)
        if not entity:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        if entity.status not in ("active", "overdue", "ended"):
            raise ValidationError(
                f"Cannot renew contract in status '{entity.status}'"
            )

        if dto.new_end_date <= entity.end_date:
            raise ValidationError("new_end_date must be after current end_date")

        old_end = entity.end_date
        old_status = entity.status
        old_rent = entity.rent_amount
        new_rent = (
            dto.new_rent_amount if dto.new_rent_amount is not None else entity.rent_amount
        )

        if entity.status == "ended":
            existing = self.repo.get_active_by_property(entity.property_id, account_id)
            if existing and existing.id != entity.id:
                raise ConflictError(
                    f"Property {entity.property_id} already has an active contract"
                )

        created_count = 0
        if self.charge_repo:
            created_count = self._append_charges_on_renew(
                entity, account_id, old_end, dto.new_end_date, new_rent
            )

        entity.end_date = dto.new_end_date
        entity.rent_amount = new_rent
        if entity.status == "ended":
            entity.status = "active"

        updated = self.repo.update(entity)

        if self.event_repo:
            description = (
                f"Срок: {format_date_ru(old_end)} → {format_date_ru(dto.new_end_date)}"
            )
            if new_rent != old_rent:
                description = (
                    f"{description}\nАренда: {format_money(old_rent, entity.currency)} → "
                    f"{format_money(new_rent, entity.currency)}"
                )
            self.event_repo.create(ContractEventEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract_id,
                event_type="renewal",
                title="Договор продлён",
                description=description,
                event_metadata={
                    "old_end_date": old_end.isoformat(),
                    "new_end_date": dto.new_end_date.isoformat(),
                    "old_rent_amount": str(old_rent),
                    "new_rent_amount": str(new_rent),
                    "old_status": old_status,
                    "charges_created": created_count,
                },
            ))

        if self.audit_service and user_id:
            self.audit_service.log(
                user_id=user_id,
                action="renew",
                entity_type="contract",
                entity_id=contract_id,
                old_data={"end_date": old_end.isoformat(), "rent_amount": str(old_rent)},
                new_data={
                    "end_date": dto.new_end_date.isoformat(),
                    "rent_amount": str(new_rent),
                },
            )

        doc_id = None
        doc_url = None
        doc_filename = None
        if dto.generate_act and self.pdf_service:
            doc = self.pdf_service.generate_renewal_act(
                contract_id, account_id, old_end, dto.new_end_date, new_rent
            )
            doc_id = doc.id
            doc_filename = doc.filename
            doc_url = f"/api/v1/documents/{doc.id}"

        return ContractLifecycleResultDTO(
            contract=ContractDTO.model_validate(updated),
            charges_created=created_count,
            document_id=doc_id,
            document_url=doc_url,
            document_filename=doc_filename,
        )

    def _recalc_charges_on_terminate(
        self,
        contract_id: UUID,
        account_id: UUID,
        effective_date: date,
    ) -> tuple[int, int]:
        """Пересчитать начисления при расторжении. Возвращает (deleted, updated)."""
        assert self.charge_repo is not None
        assert self.payment_repo is not None

        charges = list(self.charge_repo.list_by_contract(contract_id, account_id))
        paid_by_charge = {
            c.id: self.payment_repo.get_total_paid_for_charge(c.id, account_id)
            for c in charges
        }
        to_delete, to_update = plan_charges_on_terminate(
            charges, paid_by_charge, effective_date
        )

        for charge_id in to_delete:
            # Платежи с future charges → аванс договора
            for payment in self.payment_repo.list_by_charge(charge_id, account_id):
                payment.rent_charge_id = None
                self.payment_repo.update(payment)
            self.charge_repo.delete(charge_id, account_id)

        charge_map = {c.id: c for c in charges}
        for charge_id, new_amount, new_period_end in to_update:
            charge = charge_map[charge_id]
            paid = paid_by_charge.get(charge_id, Decimal("0"))
            charge.amount = new_amount
            charge.period_end = new_period_end
            charge.status = compute_charge_status(new_amount, paid, charge.due_date)
            self.charge_repo.update(charge)

        if to_delete or to_update:
            allocate_unlinked_payments(
                self.charge_repo,
                self.payment_repo,
                self.repo,
                contract_id,
                account_id,
            )

        return len(to_delete), len(to_update)

    def _append_charges_on_renew(
        self,
        contract: ContractEntity,
        account_id: UUID,
        old_end: date,
        new_end: date,
        rent_amount: Decimal,
    ) -> int:
        """Добавить начисления на продлённый период. Возвращает число созданных."""
        assert self.charge_repo is not None

        existing = list(self.charge_repo.list_by_contract(contract.id, account_id))
        try:
            schedule = plan_charges_on_renew(
                existing=existing,
                old_end_date=old_end,
                new_end_date=new_end,
                rent_amount=rent_amount,
                payment_day=contract.payment_day,
                billing_period=contract.billing_period,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        for item in schedule:
            entity = RentChargeEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract.id,
                due_date=item["due_date"],
                period_start=item["period_start"],
                period_end=item["period_end"],
                amount=item["amount"],
                currency=contract.currency,
                status="pending",
            )
            self.charge_repo.create(entity)

        if schedule and self.payment_repo is not None:
            allocate_unlinked_payments(
                self.charge_repo, self.payment_repo, self.repo,
                contract.id, account_id,
            )

        return len(schedule)

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
