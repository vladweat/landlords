"""Unit-тесты распределения аванса по начислениям."""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

from app.domain.entities import PaymentEntity, RentChargeEntity
from app.services.payment_allocation import allocate_unlinked_payments


def _advance(**kwargs) -> PaymentEntity:
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        contract_id=uuid4(),
        rent_charge_id=None,
        date_paid=date.today(),
        amount=Decimal("10000"),
        currency="RUB",
        method="transfer",
        note="Аванс",
    )
    defaults.update(kwargs)
    return PaymentEntity(**defaults)


def _charge(**kwargs) -> RentChargeEntity:
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        contract_id=uuid4(),
        due_date=date.today() + timedelta(days=5),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("10000"),
        currency="RUB",
        status="pending",
    )
    defaults.update(kwargs)
    return RentChargeEntity(**defaults)


class TestAllocateUnlinkedPayments:
    def test_noop_without_advances(self):
        charge_repo = Mock()
        payment_repo = Mock()
        charge_repo.list_unpaid_for_contract_for_update.return_value = []
        payment_repo.list_unlinked_for_contract_for_update.return_value = []
        count = allocate_unlinked_payments(
            charge_repo, payment_repo, Mock(), uuid4(), uuid4()
        )
        assert count == 0
        charge_repo.list_unpaid_for_contract_for_update.assert_called_once()

    def test_noop_without_unpaid_charges(self):
        charge_repo = Mock()
        payment_repo = Mock()
        payment_repo.list_unlinked_for_contract_for_update.return_value = [_advance()]
        charge_repo.list_unpaid_for_contract_for_update.return_value = []
        count = allocate_unlinked_payments(
            charge_repo, payment_repo, Mock(), uuid4(), uuid4()
        )
        assert count == 0
        payment_repo.create.assert_not_called()

    def test_full_allocate_deletes_advance(self):
        account_id = uuid4()
        contract_id = uuid4()
        advance = _advance(
            account_id=account_id, contract_id=contract_id, amount=Decimal("10000")
        )
        charge = _charge(
            account_id=account_id, contract_id=contract_id, amount=Decimal("10000")
        )

        charge_repo = Mock()
        payment_repo = Mock()
        contract_repo = Mock()
        payment_repo.list_unlinked_for_contract_for_update.return_value = [advance]
        charge_repo.list_unpaid_for_contract_for_update.return_value = [charge]
        charge_repo.list_by_contract.return_value = [charge]
        contract_repo.get_by_id.return_value = Mock(status="active")
        payment_repo.get_total_paid_for_charge.side_effect = [
            Decimal("0"),  # remaining calc
            Decimal("10000"),  # after allocate status
            Decimal("10000"),  # contract status check
        ]

        count = allocate_unlinked_payments(
            charge_repo, payment_repo, contract_repo, contract_id, account_id
        )
        assert count == 1
        payment_repo.create.assert_called_once()
        created = payment_repo.create.call_args[0][0]
        assert created.rent_charge_id == charge.id
        assert created.amount == Decimal("10000")
        payment_repo.delete.assert_called_once_with(advance.id, account_id)
        charge_repo.update_status.assert_called_once()
        assert charge_repo.update_status.call_args[0][2] == "paid"

    def test_partial_allocate_reduces_advance(self):
        account_id = uuid4()
        contract_id = uuid4()
        advance = _advance(
            account_id=account_id, contract_id=contract_id, amount=Decimal("15000")
        )
        charge = _charge(
            account_id=account_id, contract_id=contract_id, amount=Decimal("10000")
        )

        charge_repo = Mock()
        payment_repo = Mock()
        contract_repo = Mock()
        payment_repo.list_unlinked_for_contract_for_update.return_value = [advance]
        charge_repo.list_unpaid_for_contract_for_update.return_value = [charge]
        charge_repo.list_by_contract.return_value = [charge]
        contract_repo.get_by_id.return_value = Mock(status="active")
        payment_repo.get_total_paid_for_charge.side_effect = [
            Decimal("0"),
            Decimal("10000"),
            Decimal("10000"),
        ]

        count = allocate_unlinked_payments(
            charge_repo, payment_repo, contract_repo, contract_id, account_id
        )
        assert count == 1
        payment_repo.delete.assert_not_called()
        payment_repo.update.assert_called_once()
        assert advance.amount == Decimal("5000")

    def test_fifo_across_charges(self):
        account_id = uuid4()
        contract_id = uuid4()
        advance = _advance(
            account_id=account_id, contract_id=contract_id, amount=Decimal("15000")
        )
        c1 = _charge(
            account_id=account_id,
            contract_id=contract_id,
            amount=Decimal("10000"),
            due_date=date.today() - timedelta(days=10),
        )
        c2 = _charge(
            account_id=account_id,
            contract_id=contract_id,
            amount=Decimal("10000"),
            due_date=date.today() + timedelta(days=10),
        )

        charge_repo = Mock()
        payment_repo = Mock()
        contract_repo = Mock()
        payment_repo.list_unlinked_for_contract_for_update.return_value = [advance]
        charge_repo.list_unpaid_for_contract_for_update.return_value = [c1, c2]
        charge_repo.list_by_contract.return_value = [c1, c2]
        contract_repo.get_by_id.return_value = Mock(status="overdue")

        paid_lookup = {
            c1.id: Decimal("0"),
            c2.id: Decimal("0"),
        }

        def total_paid(charge_id, _account_id):
            return paid_lookup[charge_id]

        def create_payment(entity):
            paid_lookup[entity.rent_charge_id] = (
                paid_lookup[entity.rent_charge_id] + entity.amount
            )
            return entity

        payment_repo.get_total_paid_for_charge.side_effect = total_paid
        payment_repo.create.side_effect = create_payment

        count = allocate_unlinked_payments(
            charge_repo, payment_repo, contract_repo, contract_id, account_id
        )
        assert count == 2
        amounts = [call.args[0].amount for call in payment_repo.create.call_args_list]
        assert amounts == [Decimal("10000"), Decimal("5000")]
        charge_ids = [
            call.args[0].rent_charge_id for call in payment_repo.create.call_args_list
        ]
        assert charge_ids == [c1.id, c2.id]
        payment_repo.delete.assert_called_once_with(advance.id, account_id)
        statuses = {
            call.args[0]: call.args[2]
            for call in charge_repo.update_status.call_args_list
        }
        assert statuses[c1.id] == "paid"
        assert statuses[c2.id] == "partially_paid"
