"""Сервис управления платежами."""

from uuid import UUID, uuid4
from datetime import date

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import PaymentEntity
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
from app.domain.entities import ContractEventEntity
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
        self, account_id: UUID, dto: PaymentCreateDTO
    ) -> PaymentCreateResultDTO:
        """Создать платёж с автоматическим распределением по charges."""
        contract = self.contract_repo.get_by_id(dto.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={dto.contract_id} not found")

        if dto.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        if not dto.rent_charge_id:
            return self._auto_distribute(account_id, dto, contract)

        return self._create_linked_payment(account_id, dto, contract)

    def allocate_advance(self, contract_id: UUID, account_id: UUID) -> dict:
        """По запросу распределить аванс по неоплаченным начислениям."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        allocated_count = allocate_unlinked_payments(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )
        return {"allocated_count": allocated_count}

    def _create_linked_payment(
        self, account_id: UUID, dto: PaymentCreateDTO, contract
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

        linked_amount = min(dto.amount, charge_remaining)
        advance_amount = dto.amount - linked_amount
        created_payments: list[PaymentEntity] = []

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
                )
            )
            created_payments.append(advance)

        if self.event_repo:
            self.event_repo.create(
                ContractEventEntity(
                    id=uuid4(),
                    account_id=account_id,
                    contract_id=dto.contract_id,
                    event_type="payment",
                    title=f"Платёж: {dto.amount} {contract.currency}",
                    event_metadata={
                        "payment_id": str(linked.id),
                        "amount": float(dto.amount),
                    },
                )
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
        self, account_id: UUID, dto: PaymentCreateDTO, contract
    ) -> PaymentCreateResultDTO:
        """Автоматически распределить платёж по неоплаченным charges."""
        charges = self.charge_repo.list_unpaid_for_contract_for_update(
            dto.contract_id, account_id
        )
        unpaid = [c for c in charges if c.status != "paid"]
        unpaid.sort(key=lambda c: c.due_date)

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
            )
            created = self.payment_repo.create(entity)
            created_payments.append(created)

        if not created_payments:
            raise ValidationError("No payment created")

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

        if dto.date_paid is not None:
            entity.date_paid = dto.date_paid
        if dto.amount is not None:
            if dto.amount <= 0:
                raise ValidationError("Payment amount must be greater than 0")
            entity.amount = dto.amount
        if dto.method is not None:
            entity.method = dto.method
        if dto.note is not None:
            entity.note = dto.note

        updated = self.payment_repo.update(entity)

        if updated.rent_charge_id:
            charge = self.charge_repo.get_by_id(updated.rent_charge_id, account_id)
            if charge:
                total_paid = self.payment_repo.get_total_paid_for_charge(
                    updated.rent_charge_id, account_id
                )
                new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
                self.charge_repo.update_status(updated.rent_charge_id, account_id, new_status)

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

        charge_id = entity.rent_charge_id
        contract_id = entity.contract_id
        self.payment_repo.delete(payment_id, account_id)

        if charge_id:
            charge = self.charge_repo.get_by_id(charge_id, account_id)
            if charge:
                total_paid = self.payment_repo.get_total_paid_for_charge(charge_id, account_id)
                new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
                self.charge_repo.update_status(charge_id, account_id, new_status)

        check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )
