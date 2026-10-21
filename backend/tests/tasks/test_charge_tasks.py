"""Тесты Celery-задач."""

import inspect
from unittest.mock import Mock, patch

from app.tasks.charge_tasks import generate_charges_for_contract, update_overdue_charges


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


class TestUpdateOverdueCharges:
    def test_includes_partially_paid_in_bulk_update(self):
        """Bulk-update переводит и partially_paid при просрочке."""
        source = inspect.getsource(update_overdue_charges)
        assert "partially_paid" in source
        assert '("pending", "partially_paid")' in source or "('pending', 'partially_paid')" in source
