"""Сервис управления платежами."""

from uuid import UUID, uuid4
from datetime import date

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import PaymentEntity
from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository
from app.services.dto.payment_dto import PaymentCreateDTO, PaymentDTO, PaymentUpdateDTO
from app.domain.rules import compute_charge_status
from app.db.repositories.contract_event_repo import ContractEventRepository
from app.domain.entities import ContractEventEntity

class PaymentService:
    """Сервис управления платежами."""

    def __init__(
        self,
        payment_repo: IPaymentRepository,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        session=None,
    ) -> None:
        self.payment_repo = payment_repo
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.session = session

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
    ) -> PaymentDTO:
        """Создать платёж с автоматическим распределением по charges."""
        contract = self.contract_repo.get_by_id(dto.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={dto.contract_id} not found")

        if dto.amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        # Если не указан rent_charge_id — автоматически распределяем
        if not dto.rent_charge_id:
            return self._auto_distribute(account_id, dto, contract)

        # Если rent_charge_id указан — блокируем строку charge
        charge = self.charge_repo.get_by_id_for_update(dto.rent_charge_id, account_id)
        if not charge:
            raise NotFoundError(f"RentCharge with id={dto.rent_charge_id} not found")

        entity = PaymentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=dto.contract_id,
            rent_charge_id=dto.rent_charge_id,
            date_paid=dto.date_paid,
            amount=dto.amount,
            currency=contract.currency,
            method=dto.method,
            note=dto.note,
        )
        created = self.payment_repo.create(entity)

        # Логирование события
        from app.db.repositories.contract_event_repo import ContractEventRepository
        from app.domain.entities import ContractEventEntity
        event_repo = ContractEventRepository(self.session) if self.session else None
        if event_repo:
            event_repo.create(ContractEventEntity(
                id=uuid4(), account_id=account_id, contract_id=dto.contract_id,
                event_type="payment",
                title=f"Платёж: {dto.amount} {contract.currency}",
                event_metadata={"payment_id": str(created.id), "amount": float(dto.amount)},
            ))

        total_paid = self.payment_repo.get_total_paid_for_charge(dto.rent_charge_id, account_id)
        new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
        self.charge_repo.update_status(dto.rent_charge_id, account_id, new_status)

        _check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        return PaymentDTO.model_validate(created)


    def _auto_distribute(
        self, account_id: UUID, dto: PaymentCreateDTO, contract
    ) -> PaymentDTO:
        """Автоматически распределить платёж по неоплаченным charges."""
        charges = self.charge_repo.list_unpaid_for_contract_for_update(
            dto.contract_id, account_id
        )
        unpaid = [c for c in charges if c.status != "paid"]
        unpaid.sort(key=lambda c: c.due_date)

        remaining = dto.amount
        created_payments = []

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

        _check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            dto.contract_id, account_id,
        )

        return PaymentDTO.model_validate(created_payments[0])



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

        _check_and_update_contract_status(
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

        _check_and_update_contract_status(
            self.charge_repo, self.payment_repo, self.contract_repo,
            contract_id, account_id,
        )

def _check_and_update_contract_status(charge_repo, payment_repo, contract_repo, contract_id, account_id):
    from datetime import date as dt_date

    charges = charge_repo.list_by_contract(contract_id, account_id)
    contract = contract_repo.get_by_id(contract_id, account_id)
    if not contract:
        return

    today = dt_date.today()

    # Только прошедшие и текущие charges
    past_charges = [c for c in charges if c.due_date <= today]

    all_past_paid = all(
        payment_repo.get_total_paid_for_charge(c.id, account_id) >= c.amount
        for c in past_charges
    ) if past_charges else True

    has_overdue_unpaid = any(
        payment_repo.get_total_paid_for_charge(c.id, account_id) < c.amount
        and c.due_date < today
        for c in past_charges
    )

    if all_past_paid and contract.status == "overdue":
        contract.status = "active"
        contract_repo.update(contract)
    elif has_overdue_unpaid and contract.status == "active":
        contract.status = "overdue"
        contract_repo.update(contract)