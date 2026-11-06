"""Сервис управления платежами."""

from uuid import UUID, uuid4
from datetime import date
from decimal import Decimal

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import (
    ContractEventEntity,
    PaymentAllocationEventEntity,
    PaymentEntity,
    PaymentReceiptEntity,
    PaymentReceiptEventEntity,
)
from app.domain.interfaces import (
    IContractEventRepository,
    IContractRepository,
    IPaymentRepository,
    IRentChargeRepository,
)
from app.services.dto.payment_dto import (
    PaymentCreateDTO,
    PaymentCreateResultDTO,
    PaymentDTO,
    PaymentUpdateDTO,
)
from app.domain.rules import compute_charge_status
from app.services.contract_event_labels import (
    format_money,
    payment_method_label,
)
from app.services.contract_status import check_and_update_contract_status
from app.services.payment_allocation import allocate_unlinked_payments


class PaymentService:
    """Сервис управления платежами."""

    def __init__(
        self,
        payment_repo: IPaymentRepository,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        event_repo: IContractEventRepository | None = None,
    ) -> None:
        self.payment_repo = payment_repo
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.event_repo = event_repo

    def _log_payment_event(
        self,
        account_id: UUID,
        contract_id: UUID,
        amount: Decimal,
        currency: str,
        method: str,
        note: str | None,
        payment_id: UUID,
        receipt_id: UUID,
    ) -> None:
        """Записать событие платежа в таймлайн договора."""
        if not self.event_repo:
            return
        parts = [payment_method_label(method)]
        if note and note.strip():
            parts.append(note.strip())
        self.event_repo.create(
            ContractEventEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract_id,
                event_type="payment",
                title=f"Платёж: {format_money(amount, currency)}",
                description=", ".join(parts),
                event_metadata={
                    "payment_id": str(payment_id),
                    "amount": str(amount),
                },
                payment_receipt_id=receipt_id,
            )
        )

    def _create_receipt(
        self,
        account_id: UUID,
        dto: PaymentCreateDTO,
        currency: str,
        source: str,
    ) -> UUID:
        receipt_id = uuid4()
        self.payment_repo.create_receipt(
            PaymentReceiptEntity(
                id=receipt_id,
                account_id=account_id,
                contract_id=dto.contract_id,
                date_paid=dto.date_paid,
                original_amount=dto.amount,
                currency=currency,
                method=dto.method,
                source=source,
                note=dto.note,
            )
        )
        return receipt_id

    def _create_allocation_event(
        self,
        *,
        account_id: UUID,
        contract_id: UUID,
        receipt_id: UUID,
        charge_id: UUID,
        amount: Decimal,
    ) -> UUID:
        event_id = uuid4()
        self.payment_repo.create_allocation_event(
            PaymentAllocationEventEntity(
                id=event_id,
                account_id=account_id,
                contract_id=contract_id,
                receipt_id=receipt_id,
                rent_charge_id=charge_id,
                event_type="allocation",
                amount=amount,
            )
        )
        return event_id

    def _record_receipt_adjustment(
        self,
        entity: PaymentEntity,
        *,
        event_type: str,
        amount_delta: Decimal,
    ) -> None:
        if entity.receipt_id is None:
            return
        self.payment_repo.create_receipt_event(
            PaymentReceiptEventEntity(
                id=uuid4(),
                account_id=entity.account_id,
                contract_id=entity.contract_id,
                receipt_id=entity.receipt_id,
                event_type=event_type,
                amount_delta=amount_delta,
                resulting_date_paid=entity.date_paid,
                resulting_method=entity.method,
                resulting_note=entity.note,
            )
        )

    def _reverse_allocation(
        self, entity: PaymentEntity, *, amount: Decimal | None = None
    ) -> None:
        if entity.receipt_id is None or entity.allocation_event_id is None:
            return
        if entity.rent_charge_id is None:
            raise ValueError("An advance payment cannot reference an allocation event")
        reversal_amount = entity.amount if amount is None else amount
        self.payment_repo.create_allocation_event(
            PaymentAllocationEventEntity(
                id=uuid4(),
                account_id=entity.account_id,
                contract_id=entity.contract_id,
                receipt_id=entity.receipt_id,
                rent_charge_id=entity.rent_charge_id,
                event_type="reversal",
                amount=-reversal_amount,
                reverses_event_id=entity.allocation_event_id,
            )
        )
    def list_payments(
        self,
        account_id: UUID,
        contract_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[PaymentDTO]:
        """Получить список платежей аккаунта с фильтрацией."""
        entities = self.payment_repo.list_by_account(
            account_id=account_id,
            contract_id=contract_id,
            start_date=start_date,
            end_date=end_date,
        )
        return [PaymentDTO.model_validate(e) for e in entities]

    def list_payments_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> list[PaymentDTO]:
        """Получить список платежей по контракту."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        entities = self.payment_repo.list_by_contract(contract_id, account_id)
        return [PaymentDTO.model_validate(e) for e in entities]

    def create_payment(
        self, account_id: UUID, dto: PaymentCreateDTO, *, source: str = "manual"
    ) -> PaymentCreateResultDTO:
        """Создать платёж с автоматическим распределением по charges."""
        contract = self.contract_repo.get_by_id_for_update(dto.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={dto.contract_id} not found")

        if dto.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        if not dto.rent_charge_id:
            return self._auto_distribute(account_id, dto, contract, source)

        return self._create_linked_payment(account_id, dto, contract, source)

    def allocate_advance(self, contract_id: UUID, account_id: UUID) -> dict:
        """По запросу распределить аванс по неоплаченным начислениям."""
        contract = self.contract_repo.get_by_id_for_update(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        allocated_count = allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )
        return {"allocated_count": allocated_count}

    def _create_linked_payment(
        self, account_id: UUID, dto: PaymentCreateDTO, contract, source: str
    ) -> PaymentCreateResultDTO:
        """Платёж с явным rent_charge_id: остаток charge, избыток → аванс."""
        charge = self.charge_repo.get_by_id_for_update(dto.rent_charge_id, account_id)
        if not charge:
            raise NotFoundError(f"RentCharge with id={dto.rent_charge_id} not found")

        if charge.contract_id != dto.contract_id:
            raise ValidationError("Charge does not belong to this contract")

        total_paid = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
        charge_remaining = charge.amount - total_paid
        if charge_remaining <= 0:
            raise ValidationError("Charge is already fully paid")

        receipt_id = self._create_receipt(
            account_id, dto, contract.currency, source
        )
        linked_amount = min(dto.amount, charge_remaining)
        advance_amount = dto.amount - linked_amount
        created_payments: list[PaymentEntity] = []
        allocation_event_id = self._create_allocation_event(
            account_id=account_id,
            contract_id=dto.contract_id,
            receipt_id=receipt_id,
            charge_id=charge.id,
            amount=linked_amount,
        )

        linked = self.payment_repo.create(
            PaymentEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=dto.contract_id,
                rent_charge_id=charge.id,
                date_paid=dto.date_paid,
                amount=linked_amount,
                currency=contract.currency,
                method=dto.method,
                note=dto.note,
                receipt_id=receipt_id,
                allocation_event_id=allocation_event_id,
            )
        )
        created_payments.append(linked)

        if advance_amount > 0:
            advance = self.payment_repo.create(
                PaymentEntity(
                    id=uuid4(),
                    account_id=account_id,
                    contract_id=dto.contract_id,
                    rent_charge_id=None,
                    date_paid=dto.date_paid,
                    amount=advance_amount,
                    currency=contract.currency,
                    method=dto.method,
                    note=f"{dto.note} (аванс)" if dto.note else "Аванс",
                    receipt_id=receipt_id,
                )
            )
            created_payments.append(advance)

        self._log_payment_event(
            account_id,
            dto.contract_id,
            dto.amount,
            contract.currency,
            dto.method,
            dto.note,
            linked.id,
            receipt_id,
        )

        new_total = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
        new_status = compute_charge_status(charge.amount, new_total, charge.due_date)
        self.charge_repo.update_status(charge.id, account_id, new_status)

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        return PaymentCreateResultDTO(
            payments=[PaymentDTO.model_validate(p) for p in created_payments],
            total_amount=dto.amount,
        )

    def _auto_distribute(
        self, account_id: UUID, dto: PaymentCreateDTO, contract, source: str
    ) -> PaymentCreateResultDTO:
        """Автоматически распределить платёж по неоплаченным charges."""
        charges = self.charge_repo.list_unpaid_for_contract_for_update(
            dto.contract_id, account_id
        )
        unpaid = [c for c in charges if c.status != "paid"]
        unpaid.sort(key=lambda c: c.due_date)

        receipt_id = self._create_receipt(
            account_id, dto, contract.currency, source
        )
        remaining = dto.amount
        created_payments: list[PaymentEntity] = []

        for charge in unpaid:
            if remaining <= 0:
                break
            total_paid = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
            charge_remaining = charge.amount - total_paid
            if charge_remaining <= 0:
                continue

            pay_amount = min(remaining, charge_remaining)
            allocation_event_id = self._create_allocation_event(
                account_id=account_id,
                contract_id=dto.contract_id,
                receipt_id=receipt_id,
                charge_id=charge.id,
                amount=pay_amount,
            )
            entity = PaymentEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=dto.contract_id,
                rent_charge_id=charge.id,
                date_paid=dto.date_paid,
                amount=pay_amount,
                currency=contract.currency,
                method=dto.method,
                note=dto.note,
                receipt_id=receipt_id,
                allocation_event_id=allocation_event_id,
            )
            created = self.payment_repo.create(entity)
            created_payments.append(created)

            new_total = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
            new_status = compute_charge_status(charge.amount, new_total, charge.due_date)
            self.charge_repo.update_status(charge.id, account_id, new_status)

            remaining -= pay_amount

        # Остаток — аванс без привязки
        if remaining > 0:
            entity = PaymentEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=dto.contract_id,
                rent_charge_id=None,
                date_paid=dto.date_paid,
                amount=remaining,
                currency=contract.currency,
                method=dto.method,
                note=f"{dto.note} (аванс)" if dto.note else "Аванс",
                receipt_id=receipt_id,
            )
            created = self.payment_repo.create(entity)
            created_payments.append(created)

        if not created_payments:
            raise ValidationError("No payment created")

        self._log_payment_event(
            account_id,
            dto.contract_id,
            dto.amount,
            contract.currency,
            dto.method,
            dto.note,
            created_payments[0].id,
            receipt_id,
        )

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        return PaymentCreateResultDTO(
            payments=[PaymentDTO.model_validate(p) for p in created_payments],
            total_amount=dto.amount,
        )

    def update_payment(
        self, payment_id: UUID, account_id: UUID, dto: PaymentUpdateDTO
    ) -> PaymentDTO:
        """Обновить платёж."""
        entity = self.payment_repo.get_by_id(payment_id, account_id)
        if not entity:
            raise NotFoundError(f"Payment with id={payment_id} not found")
        contract = self.contract_repo.get_by_id_for_update(entity.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={entity.contract_id} not found")
        if entity.rent_charge_id:
            self.charge_repo.get_by_id_for_update(entity.rent_charge_id, account_id)
        entity = self.payment_repo.get_by_id_for_update(payment_id, account_id)
        if not entity:
            raise NotFoundError(f"Payment with id={payment_id} not found")

        original_amount = entity.amount
        original_metadata = (entity.date_paid, entity.method, entity.note)
        if dto.date_paid is not None:
            entity.date_paid = dto.date_paid
        if dto.amount is not None:
            if dto.amount <= 0:
                raise ValidationError("Payment amount must be greater than 0")
            if entity.rent_charge_id:
                charge = self.charge_repo.get_by_id_for_update(
                    entity.rent_charge_id, account_id
                )
                if charge:
                    total_paid = self.payment_repo.get_total_paid_for_charge(
                        charge.id, account_id
                    )
                    if total_paid - entity.amount + dto.amount > charge.amount:
                        raise ValidationError("Payment exceeds the remaining charge amount")
            entity.amount = dto.amount
        if dto.method is not None:
            entity.method = dto.method
        if dto.note is not None:
            entity.note = dto.note

        amount_changed = entity.amount != original_amount
        metadata_changed = (entity.date_paid, entity.method, entity.note) != original_metadata
        if entity.receipt_id is not None and (amount_changed or metadata_changed):
            self._record_receipt_adjustment(
                entity,
                event_type="correction",
                amount_delta=entity.amount - original_amount,
            )
        if amount_changed and entity.allocation_event_id is not None:
            self._reverse_allocation(entity, amount=original_amount)
            assert entity.receipt_id is not None and entity.rent_charge_id is not None
            entity.allocation_event_id = self._create_allocation_event(
                account_id=entity.account_id,
                contract_id=entity.contract_id,
                receipt_id=entity.receipt_id,
                charge_id=entity.rent_charge_id,
                amount=entity.amount,
            )

        updated = self.payment_repo.update(entity)

        if updated.rent_charge_id:
            charge = self.charge_repo.get_by_id_for_update(updated.rent_charge_id, account_id)
            if charge:
                total_paid = self.payment_repo.get_total_paid_for_charge(
                    updated.rent_charge_id, account_id
                )
                new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
                self.charge_repo.update_status(updated.rent_charge_id, account_id, new_status)

        allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            updated.contract_id, account_id,
        )

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            updated.contract_id, account_id,
        )

        return PaymentDTO.model_validate(updated)

    def delete_payment(self, payment_id: UUID, account_id: UUID) -> None:
        """Удалить платёж."""
        entity = self.payment_repo.get_by_id(payment_id, account_id)
        if not entity:
            raise NotFoundError(f"Payment with id={payment_id} not found")
        contract = self.contract_repo.get_by_id_for_update(entity.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={entity.contract_id} not found")
        charge_id = entity.rent_charge_id
        if charge_id:
            self.charge_repo.get_by_id_for_update(charge_id, account_id)
        entity = self.payment_repo.get_by_id_for_update(payment_id, account_id)
        if not entity:
            raise NotFoundError(f"Payment with id={payment_id} not found")

        contract_id = entity.contract_id
        self._record_receipt_adjustment(
            entity, event_type="cancellation", amount_delta=-entity.amount
        )
        self._reverse_allocation(entity)
        self.payment_repo.delete(payment_id, account_id)

        if charge_id:
            charge = self.charge_repo.get_by_id_for_update(charge_id, account_id)
            if charge:
                total_paid = self.payment_repo.get_total_paid_for_charge(charge_id, account_id)
                new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
                self.charge_repo.update_status(charge_id, account_id, new_status)

        allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )
