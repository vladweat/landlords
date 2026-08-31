"""Пересчёт статуса контракта по начислениям и платежам."""

from datetime import date as dt_date
from uuid import UUID

from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository


def check_and_update_contract_status(
    charge_repo: IRentChargeRepository,
    payment_repo: IPaymentRepository,
    contract_repo: IContractRepository,
    contract_id: UUID,
    account_id: UUID,
) -> None:
    charges = charge_repo.list_by_contract(contract_id, account_id)
    contract = contract_repo.get_by_id(contract_id, account_id)
    if not contract:
        return

    today = dt_date.today()
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
