"""Unit-тесты сервиса платежей."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractEntity, PaymentEntity, RentChargeEntity
from app.services.dto.payment_dto import PaymentCreateDTO, PaymentUpdateDTO
from app.services.payment_service import PaymentService


@pytest.fixture
def mock_payment_repo():
    repo = Mock()
    repo.create.return_value = PaymentEntity(
        id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
        date_paid=date.today(), amount=Decimal("1000"), currency="RUB", method="bank",
    )
    repo.get_total_paid_for_charge.return_value = Decimal("0")
    repo.list_unlinked_for_contract_for_update.return_value = []
    return repo


@pytest.fixture
def mock_contract_repo():
    repo = Mock()
    repo.get_by_id.return_value = ContractEntity(
        id=uuid4(), account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
        start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
        currency="RUB", payment_day=5, status="active",
    )
    return repo


@pytest.fixture
def mock_charge_repo():
    repo = Mock()
    repo.get_by_id_for_update.return_value = RentChargeEntity(
        id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
        due_date=date.today(), period_start=date.today(), period_end=date.today(),
        amount=Decimal("1000"), currency="RUB", status="pending",
    )
    repo.list_unpaid_for_contract_for_update.return_value = []
    repo.list_by_contract.return_value = []
    return repo


@pytest.fixture
def payment_service(mock_payment_repo, mock_contract_repo, mock_charge_repo):
    return PaymentService(mock_payment_repo, mock_contract_repo, mock_charge_repo)


class TestCreatePayment:
    def test_negative_amount_raises(self):
        """Отрицательная сумма — ошибка валидации DTO."""
        with pytest.raises(PydanticValidationError):
            PaymentCreateDTO(
                contract_id=uuid4(), date_paid=date.today(),
                amount=Decimal("-100"), method="bank",
            )

    def test_zero_amount_raises(self):
        """Нулевая сумма — ошибка валидации."""
        with pytest.raises(PydanticValidationError):
            PaymentCreateDTO(
                contract_id=uuid4(), date_paid=date.today(),
                amount=Decimal("0"), method="bank",
            )

    def test_success_without_charge(self, payment_service, mock_payment_repo):
        """Успешное создание платежа без привязки к charge."""
        mock_payment_repo.create.return_value = PaymentEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            date_paid=date.today(), amount=Decimal("1000"), currency="RUB", method="bank",
        )
        dto = PaymentCreateDTO(
            contract_id=uuid4(), date_paid=date.today(),
            amount=Decimal("1000"), method="bank",
        )
        result = payment_service.create_payment(uuid4(), dto)
        assert result.total_amount == Decimal("1000")
        assert len(result.payments) == 1
        assert result.payments[0].amount == Decimal("1000")

    def test_success_with_charge(
        self, payment_service, mock_payment_repo, mock_charge_repo, mock_contract_repo
    ):
        """Успешное создание платежа с привязкой к charge."""
        contract_id = uuid4()
        charge_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        mock_charge_repo.get_by_id_for_update.return_value = RentChargeEntity(
            id=charge_id, account_id=uuid4(), contract_id=contract_id,
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="pending",
        )
        mock_payment_repo.create.return_value = PaymentEntity(
            id=uuid4(), account_id=uuid4(), contract_id=contract_id,
            rent_charge_id=charge_id, date_paid=date.today(),
            amount=Decimal("500"), currency="RUB", method="cash",
        )
        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("500"), method="cash", rent_charge_id=charge_id,
        )
        result = payment_service.create_payment(uuid4(), dto)
        assert len(result.payments) == 1
        assert result.payments[0].rent_charge_id == charge_id

    def test_linked_excess_goes_to_advance(
        self, payment_service, mock_payment_repo, mock_charge_repo, mock_contract_repo
    ):
        """Избыток сверх остатка charge уходит в аванс."""
        contract_id = uuid4()
        charge_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        mock_charge_repo.get_by_id_for_update.return_value = RentChargeEntity(
            id=charge_id, account_id=uuid4(), contract_id=contract_id,
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="partially_paid",
        )
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("400")

        created = []

        def create_side_effect(entity):
            created.append(entity)
            return entity

        mock_payment_repo.create.side_effect = create_side_effect

        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("800"), method="transfer", rent_charge_id=charge_id,
        )
        result = payment_service.create_payment(uuid4(), dto)
        assert result.total_amount == Decimal("800")
        assert len(result.payments) == 2
        assert created[0].amount == Decimal("600")
        assert created[0].rent_charge_id == charge_id
        assert created[1].amount == Decimal("200")
        assert created[1].rent_charge_id is None

    def test_charge_wrong_contract(
        self, payment_service, mock_charge_repo, mock_contract_repo
    ):
        """Charge от другого договора — ошибка."""
        contract_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        mock_charge_repo.get_by_id_for_update.return_value = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="pending",
        )
        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("500"), method="cash", rent_charge_id=uuid4(),
        )
        with pytest.raises(ValidationError, match="does not belong"):
            payment_service.create_payment(uuid4(), dto)

    def test_auto_distribute_returns_all_splits(
        self, payment_service, mock_payment_repo, mock_charge_repo, mock_contract_repo
    ):
        """Автораспределение возвращает все split-платежи."""
        contract_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        c1 = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=contract_id,
            due_date=date(2026, 1, 5), period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31), amount=Decimal("1000"),
            currency="RUB", status="pending",
        )
        c2 = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=contract_id,
            due_date=date(2026, 2, 5), period_start=date(2026, 2, 1),
            period_end=date(2026, 2, 28), amount=Decimal("1000"),
            currency="RUB", status="pending",
        )
        mock_charge_repo.list_unpaid_for_contract_for_update.return_value = [c1, c2]
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("0")

        created = []

        def create_side_effect(entity):
            created.append(entity)
            return entity

        mock_payment_repo.create.side_effect = create_side_effect

        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("2500"), method="transfer",
        )
        result = payment_service.create_payment(uuid4(), dto)
        assert result.total_amount == Decimal("2500")
        assert len(result.payments) == 3
        assert created[0].amount == Decimal("1000")
        assert created[1].amount == Decimal("1000")
        assert created[2].amount == Decimal("500")
        assert created[2].rent_charge_id is None

    def test_auto_distribute_creates_contract_event(
        self, mock_payment_repo, mock_contract_repo, mock_charge_repo
    ):
        """Автораспределение пишет событие платежа в таймлайн договора."""
        event_repo = Mock()
        service = PaymentService(
            mock_payment_repo, mock_contract_repo, mock_charge_repo, event_repo
        )
        contract_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        charge = RentChargeEntity(
            id=uuid4(), account_id=uuid4(), contract_id=contract_id,
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="pending",
        )
        mock_charge_repo.list_unpaid_for_contract_for_update.return_value = [charge]
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
        mock_payment_repo.create.side_effect = lambda e: e
        mock_payment_repo.list_unlinked_for_contract_for_update.return_value = []
        mock_charge_repo.list_by_contract.return_value = [charge]

        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("1000"), method="transfer", note="за январь",
        )
        service.create_payment(uuid4(), dto)

        event_repo.create.assert_called_once()
        event = event_repo.create.call_args[0][0]
        assert event.event_type == "payment"
        assert event.title == "Платёж: 1\u00a0000 RUB"
        assert "перевод" in event.description
        assert "за январь" in event.description

    def test_linked_payment_creates_russian_event(
        self, mock_payment_repo, mock_contract_repo, mock_charge_repo
    ):
        """Платёж с charge пишет русскоязычное событие."""
        event_repo = Mock()
        service = PaymentService(
            mock_payment_repo, mock_contract_repo, mock_charge_repo, event_repo
        )
        contract_id = uuid4()
        charge_id = uuid4()
        mock_contract_repo.get_by_id.return_value = ContractEntity(
            id=contract_id, account_id=uuid4(), property_id=uuid4(), tenant_id=uuid4(),
            start_date=date.today(), end_date=date.today(), rent_amount=Decimal("1000"),
            currency="RUB", payment_day=5, status="active",
        )
        mock_charge_repo.get_by_id_for_update.return_value = RentChargeEntity(
            id=charge_id, account_id=uuid4(), contract_id=contract_id,
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="pending",
        )
        mock_payment_repo.create.side_effect = lambda e: e
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("500")
        mock_payment_repo.list_unlinked_for_contract_for_update.return_value = []
        mock_charge_repo.list_by_contract.return_value = []

        dto = PaymentCreateDTO(
            contract_id=contract_id, date_paid=date.today(),
            amount=Decimal("500"), method="cash", rent_charge_id=charge_id,
        )
        service.create_payment(uuid4(), dto)

        event = event_repo.create.call_args[0][0]
        assert event.event_type == "payment"
        assert event.title == "Платёж: 500 RUB"
        assert event.description == "наличные"

    def test_contract_not_found(self, payment_service, mock_contract_repo):
        """Контракт не найден."""
        mock_contract_repo.get_by_id.return_value = None
        dto = PaymentCreateDTO(
            contract_id=uuid4(), date_paid=date.today(),
            amount=Decimal("1000"), method="bank",
        )
        with pytest.raises(NotFoundError):
            payment_service.create_payment(uuid4(), dto)

    def test_charge_not_found(self, payment_service, mock_charge_repo):
        """Charge не найден."""
        mock_charge_repo.get_by_id_for_update.return_value = None
        dto = PaymentCreateDTO(
            contract_id=uuid4(), date_paid=date.today(),
            amount=Decimal("1000"), method="bank", rent_charge_id=uuid4(),
        )
        with pytest.raises(NotFoundError):
            payment_service.create_payment(uuid4(), dto)


class TestUpdatePayment:
    def test_success(self, payment_service, mock_payment_repo):
        """Успешное обновление."""
        payment_id = uuid4()
        mock_payment_repo.get_by_id.return_value = PaymentEntity(
            id=payment_id, account_id=uuid4(), contract_id=uuid4(),
            date_paid=date.today(), amount=Decimal("1000"), currency="RUB", method="bank",
        )
        mock_payment_repo.update.return_value = PaymentEntity(
            id=payment_id, account_id=uuid4(), contract_id=uuid4(),
            date_paid=date.today(), amount=Decimal("2000"), currency="RUB", method="transfer",
        )
        dto = PaymentUpdateDTO(amount=Decimal("2000"), method="transfer")
        result = payment_service.update_payment(payment_id, uuid4(), dto)
        assert result.amount == Decimal("2000")
        assert result.method == "transfer"

    def test_not_found(self, payment_service, mock_payment_repo):
        """Платёж не найден."""
        mock_payment_repo.get_by_id.return_value = None
        dto = PaymentUpdateDTO(amount=Decimal("1000"))
        with pytest.raises(NotFoundError):
            payment_service.update_payment(uuid4(), uuid4(), dto)

    def test_zero_amount_raises(self):
        """Нулевая сумма — ошибка валидации DTO."""
        with pytest.raises(PydanticValidationError):
            PaymentUpdateDTO(amount=Decimal("0"))


class TestDeletePayment:
    def test_success(self, payment_service, mock_payment_repo, mock_charge_repo):
        """Успешное удаление."""
        charge_id = uuid4()
        mock_payment_repo.get_by_id.return_value = PaymentEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            rent_charge_id=charge_id, date_paid=date.today(),
            amount=Decimal("1000"), currency="RUB", method="bank",
        )
        mock_payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
        mock_charge_repo.get_by_id.return_value = RentChargeEntity(
            id=charge_id, account_id=uuid4(), contract_id=uuid4(),
            due_date=date.today(), period_start=date.today(), period_end=date.today(),
            amount=Decimal("1000"), currency="RUB", status="paid",
        )
        payment_service.delete_payment(uuid4(), uuid4())
        mock_payment_repo.delete.assert_called_once()

    def test_not_found(self, payment_service, mock_payment_repo):
        """Платёж не найден."""
        mock_payment_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            payment_service.delete_payment(uuid4(), uuid4())

    def test_delete_without_charge(self, payment_service, mock_payment_repo):
        """Удаление платежа без charge."""
        mock_payment_repo.get_by_id.return_value = PaymentEntity(
            id=uuid4(), account_id=uuid4(), contract_id=uuid4(),
            rent_charge_id=None, date_paid=date.today(),
            amount=Decimal("1000"), currency="RUB", method="bank",
        )
        payment_service.delete_payment(uuid4(), uuid4())
        mock_payment_repo.delete.assert_called_once()
