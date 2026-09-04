"""Unit-тесты продления и расторжения договора."""

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractEntity, RentChargeEntity
from app.domain.rules import (
    plan_charges_on_renew,
    plan_charges_on_terminate,
    prorate_charge_amount,
)
from app.services.contract_service import ContractService
from app.services.dto.contract_dto import ContractRenewDTO, ContractTerminateDTO


def _contract(**kwargs) -> ContractEntity:
    defaults = dict(
        id=uuid4(),
        account_id=uuid4(),
        property_id=uuid4(),
        tenant_id=uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_amount=Decimal("30000.00"),
        currency="RUB",
        billing_period="monthly",
        payment_day=5,
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return ContractEntity(**defaults)


def _charge(contract_id, account_id, period_start, period_end, amount="30000.00") -> RentChargeEntity:
    return RentChargeEntity(
        id=uuid4(),
        account_id=account_id,
        contract_id=contract_id,
        due_date=period_start.replace(day=min(5, 28)),
        period_start=period_start,
        period_end=period_end,
        amount=Decimal(amount),
        currency="RUB",
        status="pending",
    )


class TestProrateAndPlan:
    def test_prorate_half_month(self):
        amount = prorate_charge_amount(
            Decimal("30000"), date(2026, 3, 1), date(2026, 3, 31), date(2026, 3, 16)
        )
        # 15/30 дней
        assert amount == Decimal("15000.00")

    def test_plan_terminate_deletes_future(self):
        account_id = uuid4()
        contract_id = uuid4()
        current = _charge(contract_id, account_id, date(2026, 3, 1), date(2026, 4, 1))
        future = _charge(contract_id, account_id, date(2026, 4, 1), date(2026, 5, 1))
        past = _charge(contract_id, account_id, date(2026, 2, 1), date(2026, 3, 1))

        to_delete, to_update = plan_charges_on_terminate(
            [past, current, future],
            {past.id: Decimal("0"), current.id: Decimal("0"), future.id: Decimal("0")},
            date(2026, 3, 16),
        )
        assert future.id in to_delete
        assert past.id not in to_delete
        assert any(u[0] == current.id for u in to_update)

    def test_plan_terminate_deletes_future_even_if_paid(self):
        """Future charge с платежами тоже в to_delete (сервис отвяжет → аванс)."""
        account_id = uuid4()
        contract_id = uuid4()
        future = _charge(contract_id, account_id, date(2026, 4, 1), date(2026, 5, 1))

        to_delete, to_update = plan_charges_on_terminate(
            [future],
            {future.id: Decimal("30000")},
            date(2026, 3, 16),
        )
        assert future.id in to_delete
        assert to_update == []

    def test_plan_renew_appends(self):
        account_id = uuid4()
        contract_id = uuid4()
        existing = [
            _charge(contract_id, account_id, date(2026, 11, 1), date(2026, 12, 1)),
            _charge(contract_id, account_id, date(2026, 12, 1), date(2026, 12, 31)),
        ]
        schedule = plan_charges_on_renew(
            existing=existing,
            old_end_date=date(2026, 12, 31),
            new_end_date=date(2027, 3, 31),
            rent_amount=Decimal("32000"),
            payment_day=5,
        )
        assert len(schedule) >= 2
        assert all(item["period_start"] >= date(2026, 12, 31) for item in schedule)


class TestTerminateRenewService:
    @pytest.fixture
    def repos(self):
        contract_repo = Mock()
        charge_repo = Mock()
        payment_repo = Mock()
        event_repo = Mock()
        return contract_repo, charge_repo, payment_repo, event_repo

    def test_terminate_success(self, repos):
        contract_repo, charge_repo, payment_repo, event_repo = repos
        contract = _contract()
        future = _charge(
            contract.id, contract.account_id, date(2026, 6, 1), date(2026, 7, 1)
        )
        current = _charge(
            contract.id, contract.account_id, date(2026, 3, 1), date(2026, 4, 1)
        )
        contract_repo.get_by_id.return_value = contract
        contract_repo.update.side_effect = lambda e: e
        charge_repo.list_by_contract.return_value = [current, future]
        charge_repo.list_unpaid_for_contract_for_update.return_value = []
        payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
        payment_repo.list_by_charge.return_value = []
        payment_repo.list_unlinked_for_contract_for_update.return_value = []

        service = ContractService(
            contract_repo, charge_repo, payment_repo, event_repo, pdf_service=None
        )
        result = service.terminate_contract(
            contract.id,
            contract.account_id,
            ContractTerminateDTO(
                effective_date=date(2026, 3, 15),
                termination_reason="Досрочное расторжение по соглашению",
                generate_act=False,
            ),
        )
        assert result.contract.status == "terminated"
        assert result.charges_deleted == 1
        assert result.charges_updated == 1
        charge_repo.delete.assert_called_once_with(future.id, contract.account_id)
        event_repo.create.assert_called_once()

    def test_terminate_unlinks_payments_on_future_charges(self, repos):
        """Платежи с future charge отвязываются в аванс перед удалением."""
        from app.domain.entities import PaymentEntity

        contract_repo, charge_repo, payment_repo, event_repo = repos
        contract = _contract()
        future = _charge(
            contract.id, contract.account_id, date(2026, 6, 1), date(2026, 7, 1)
        )
        current = _charge(
            contract.id, contract.account_id, date(2026, 3, 1), date(2026, 4, 1)
        )
        linked = PaymentEntity(
            id=uuid4(),
            account_id=contract.account_id,
            contract_id=contract.id,
            rent_charge_id=future.id,
            date_paid=date(2026, 3, 1),
            amount=Decimal("30000"),
            currency="RUB",
            method="transfer",
        )
        contract_repo.get_by_id.return_value = contract
        contract_repo.update.side_effect = lambda e: e
        charge_repo.list_by_contract.return_value = [current, future]
        charge_repo.list_unpaid_for_contract_for_update.return_value = [current]
        payment_repo.get_total_paid_for_charge.side_effect = (
            lambda cid, _aid: Decimal("30000") if cid == future.id else Decimal("0")
        )
        payment_repo.list_by_charge.return_value = [linked]
        payment_repo.list_unlinked_for_contract_for_update.return_value = []
        payment_repo.update.side_effect = lambda e: e

        service = ContractService(
            contract_repo, charge_repo, payment_repo, event_repo, pdf_service=None
        )
        result = service.terminate_contract(
            contract.id,
            contract.account_id,
            ContractTerminateDTO(
                effective_date=date(2026, 3, 15),
                termination_reason="test",
                generate_act=False,
            ),
        )
        assert result.charges_deleted == 1
        payment_repo.update.assert_called()
        updated_payment = payment_repo.update.call_args[0][0]
        assert updated_payment.rent_charge_id is None
        charge_repo.delete.assert_called_once_with(future.id, contract.account_id)
    def test_terminate_invalid_status(self, repos):
        contract_repo, charge_repo, payment_repo, event_repo = repos
        contract = _contract(status="ended")
        contract_repo.get_by_id.return_value = contract
        service = ContractService(contract_repo, charge_repo, payment_repo, event_repo)
        with pytest.raises(ValidationError, match="Cannot terminate"):
            service.terminate_contract(
                contract.id,
                contract.account_id,
                ContractTerminateDTO(
                    effective_date=date(2026, 6, 1),
                    termination_reason="test",
                    generate_act=False,
                ),
            )

    def test_renew_success(self, repos):
        contract_repo, charge_repo, payment_repo, event_repo = repos
        contract = _contract(end_date=date(2026, 6, 30))
        contract_repo.get_by_id.return_value = contract
        contract_repo.update.side_effect = lambda e: e
        charge_repo.list_by_contract.return_value = []
        payment_repo.list_unlinked_for_contract_for_update.return_value = []
        charge_repo.list_unpaid_for_contract_for_update.return_value = []

        service = ContractService(
            contract_repo, charge_repo, payment_repo, event_repo, pdf_service=None
        )
        result = service.renew_contract(
            contract.id,
            contract.account_id,
            ContractRenewDTO(
                new_end_date=date(2026, 12, 31),
                new_rent_amount=Decimal("35000"),
                generate_act=False,
            ),
        )
        assert result.contract.end_date == date(2026, 12, 31)
        assert result.contract.rent_amount == Decimal("35000")
        assert result.charges_created >= 1
        assert charge_repo.create.call_count == result.charges_created

    def test_renew_not_found(self, repos):
        contract_repo, charge_repo, payment_repo, event_repo = repos
        contract_repo.get_by_id.return_value = None
        service = ContractService(contract_repo, charge_repo, payment_repo, event_repo)
        with pytest.raises(NotFoundError):
            service.renew_contract(
                uuid4(),
                uuid4(),
                ContractRenewDTO(new_end_date=date(2027, 1, 1), generate_act=False),
            )
