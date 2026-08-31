"""Тесты Celery-задач."""

from unittest.mock import Mock, patch
from datetime import datetime

import pytest

from app.tasks.charge_tasks import generate_charges_for_contract


class TestGenerateCharges:
    def test_task_returns_success(self):
        """Задача возвращает success (с моком)."""
        with patch(
            "app.tasks.charge_tasks.SessionLocal"
        ) as mock_session, patch(
            "app.tasks.charge_tasks.RentChargeRepository"
        ) as mock_charge_repo, patch(
            "app.tasks.charge_tasks.PaymentRepository"
        ), patch(
            "app.tasks.charge_tasks.ContractRepository"
        ) as mock_contract_repo:
            from app.domain.entities import ContractEntity
            from datetime import date
            from decimal import Decimal
            from uuid import uuid4

            mock_contract_repo.return_value.get_by_id.return_value = ContractEntity(
                id=uuid4(), account_id=uuid4(), property_id=uuid4(),
                tenant_id=uuid4(), start_date=date.today(), end_date=date.today(),
                rent_amount=Decimal("1000"), currency="RUB", payment_day=5,
                status="active",
            )
            mock_charge_repo.return_value.list_by_contract.return_value = []
            mock_charge_repo.return_value.create.return_value = Mock()

            result = generate_charges_for_contract(
                account_id="00000000-0000-0000-0000-000000000001",
                contract_id="00000000-0000-0000-0000-000000000002",
            )
            assert result["status"] == "success"
            assert "charges_created" in result