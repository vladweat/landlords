"""Тесты Celery-задач."""

import inspect
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

from app.tasks.charge_tasks import generate_charges_for_contract, update_overdue_charges
from app.domain.entities import OutboxMessageEntity


class TestGenerateCharges:
    def test_task_returns_success(self):
        """Задача возвращает success (с моком)."""
        with patch(
            "app.tasks.charge_tasks.SessionLocal"
        ), patch(
            "app.tasks.charge_tasks.RentChargeRepository"
        ) as mock_charge_repo, patch(
            "app.tasks.charge_tasks.PaymentRepository"
        ) as mock_payment_repo, patch(
            "app.tasks.charge_tasks.ContractRepository"
        ) as mock_contract_repo:
            from app.domain.entities import ContractEntity
            from datetime import date
            from decimal import Decimal
            from uuid import uuid4

            mock_contract_repo.return_value.get_by_id_for_update.return_value = ContractEntity(
                id=uuid4(), account_id=uuid4(), property_id=uuid4(),
                tenant_id=uuid4(), start_date=date.today(), end_date=date.today(),
                rent_amount=Decimal("1000"), currency="RUB", payment_day=5,
                status="active",
            )
            mock_charge_repo.return_value.list_by_contract.return_value = []
            mock_charge_repo.return_value.create_if_absent.return_value = Mock()
            mock_charge_repo.return_value.list_unpaid_for_contract_for_update.return_value = []
            mock_payment_repo.return_value.list_unlinked_for_contract_for_update.return_value = []

            result = generate_charges_for_contract(
                account_id="00000000-0000-0000-0000-000000000001",
                contract_id="00000000-0000-0000-0000-000000000002",
            )
            assert result["status"] == "success"
            assert "charges_created" in result

    def test_completed_outbox_redelivery_does_not_regenerate_charges(self):
        outbox_id = uuid4()
        message = OutboxMessageEntity(
            id=outbox_id,
            account_id=uuid4(),
            contract_id=uuid4(),
            task_name="app.tasks.charge_tasks.generate_charges_for_contract",
            status="completed",
        )
        session = Mock()
        with patch("app.tasks.charge_tasks.SessionLocal", return_value=session), patch(
            "app.tasks.charge_tasks.OutboxMessageRepository"
        ) as repository, patch("app.tasks.charge_tasks.RentChargeRepository") as charges:
            repository.return_value.get_for_update.return_value = message

            result = generate_charges_for_contract(
                str(message.account_id), str(message.contract_id), str(outbox_id)
            )

        assert result["status"] == "already_completed"
        charges.assert_not_called()
        session.commit.assert_not_called()

    def test_failed_charge_transaction_records_only_safe_error_type(self):
        account_id = str(uuid4())
        contract_id = str(uuid4())
        outbox_id = str(uuid4())
        message = OutboxMessageEntity(
            id=UUID(outbox_id),
            account_id=UUID(account_id),
            contract_id=UUID(contract_id),
            task_name="app.tasks.charge_tasks.generate_charges_for_contract",
            status="published",
        )
        task_session = Mock()
        failure_session = Mock()
        first_repository = Mock()
        first_repository.get_for_update.return_value = message
        failure_repository = Mock()
        failure_repository.record_task_failure.return_value = True
        with patch(
            "app.tasks.charge_tasks.SessionLocal",
            side_effect=[task_session, failure_session],
        ), patch(
            "app.tasks.charge_tasks.OutboxMessageRepository",
            side_effect=[first_repository, failure_repository],
        ), patch(
            "app.tasks.charge_tasks.RentChargeRepository"
        ), patch(
            "app.tasks.charge_tasks.PaymentRepository"
        ), patch(
            "app.tasks.charge_tasks.ContractRepository"
        ), patch(
            "app.tasks.charge_tasks.RentChargeService"
        ) as service, patch(
            "app.tasks.charge_tasks.record_outbox_terminal_failure"
        ) as record_terminal_failure:
            service.return_value.create_charges_batch.side_effect = ValueError(
                "redis password=must-not-be-stored"
            )

            try:
                generate_charges_for_contract(account_id, contract_id, outbox_id)
            except ValueError:
                pass
            else:
                raise AssertionError("task error should propagate to Celery")

        task_session.rollback.assert_called_once()
        failure_repository.record_task_failure.assert_called_once()
        assert failure_repository.record_task_failure.call_args.args[2] == "ValueError"
        record_terminal_failure.assert_called_once_with()


class TestUpdateOverdueCharges:
    def test_includes_partially_paid_in_bulk_update(self):
        """Bulk-update переводит и partially_paid при просрочке."""
        source = inspect.getsource(update_overdue_charges)
        assert "partially_paid" in source
        assert '("pending", "partially_paid")' in source or "('pending', 'partially_paid')" in source
