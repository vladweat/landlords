"""Распределение неаллоцированных платежей (аванса) по начислениям."""

from decimal import Decimal
from uuid import UUID, uuid4

from app.domain.entities import PaymentEntity
from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository
from app.domain.rules import compute_charge_status
from app.services.contract_status import check_and_update_contract_status


def allocate_unlinked_payments(
    charge_repo: IRentChargeRepository,
    payment_repo: IPaymentRepository,
    contract_repo: IContractRepository,
    contract_id: UUID,
    account_id: UUID,
) -> int:
    """Списать аванс (payments без rent_charge_id) на неоплаченные charges FIFO.

    Returns:
        Число созданных linked-платежей.
    """
    # Общий lock для операций по контракту задаёт порядок: contract -> charges -> payments.
    contract_repo.get_by_id_for_update(contract_id, account_id)
    unpaid = list(charge_repo.list_unpaid_for_contract_for_update(contract_id, account_id))
    advances = list(
        payment_repo.list_unlinked_for_contract_for_update(contract_id, account_id)
    )
    if not advances:
        return 0
    if not unpaid:
        return 0

    # Остаток по каждому charge с учётом уже привязанных платежей
    remaining_by_charge: dict[UUID, Decimal] = {}
    for charge in unpaid:
        paid = payment_repo.get_total_paid_for_charge(charge.id, account_id)
        left = charge.amount - paid
        if left > 0:
            remaining_by_charge[charge.id] = left

    if not remaining_by_charge:
        return 0

    charge_by_id = {c.id: c for c in unpaid}
    allocated_count = 0
    touched_charge_ids: set[UUID] = set()

    for advance in advances:
        advance_left = advance.amount
        if advance_left <= 0:
            continue

        for charge_id in list(remaining_by_charge.keys()):
            if advance_left <= 0:
                break
            charge_left = remaining_by_charge[charge_id]
            if charge_left <= 0:
                continue

            pay_amount = min(advance_left, charge_left)
            charge = charge_by_id[charge_id]
            payment_repo.create(
                PaymentEntity(
                    id=uuid4(),
                    account_id=account_id,
                    contract_id=contract_id,
                    rent_charge_id=charge_id,
                    date_paid=advance.date_paid,
                    amount=pay_amount,
                    currency=advance.currency,
                    method=advance.method,
                    note=advance.note,
                )
            )
            allocated_count += 1
            touched_charge_ids.add(charge_id)

            advance_left -= pay_amount
            remaining_by_charge[charge_id] = charge_left - pay_amount
            if remaining_by_charge[charge_id] <= 0:
                del remaining_by_charge[charge_id]

        if advance_left <= 0:
            payment_repo.delete(advance.id, account_id)
        elif advance_left < advance.amount:
            advance.amount = advance_left
            payment_repo.update(advance)

    for charge_id in sorted(touched_charge_ids, key=lambda cid: charge_by_id[cid].due_date):
        charge = charge_by_id[charge_id]
        total_paid = payment_repo.get_total_paid_for_charge(charge_id, account_id)
        new_status = compute_charge_status(charge.amount, total_paid, charge.due_date)
        charge_repo.update_status(charge_id, account_id, new_status)

    if allocated_count:
        check_and_update_contract_status(
            charge_repo, payment_repo, contract_repo, contract_id, account_id
        )

    return allocated_count
