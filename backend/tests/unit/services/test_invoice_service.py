"""Unit-тесты сервиса квитанций."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError
from app.domain.entities import (
    AccountEntity,
    ContractEntity,
    DocumentEntity,
    InvoiceEntity,
    PropertyEntity,
    RentChargeEntity,
    TenantEntity,
)
from app.services.invoice_service import InvoiceService


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def charge(account_id):
    return RentChargeEntity(
        id=uuid4(),
        account_id=account_id,
        contract_id=uuid4(),
        due_date=date.today() + timedelta(days=5),
        period_start=date.today(),
        period_end=date.today() + timedelta(days=30),
        amount=Decimal("50000"),
        currency="RUB",
        status="pending",
    )


@pytest.fixture
def service(account_id, charge):
    invoice_repo = Mock()
    charge_repo = Mock()
    payment_repo = Mock()
    contract_repo = Mock()
    property_repo = Mock()
    tenant_repo = Mock()
    account_repo = Mock()
    document_repo = Mock()
    pdf_service = Mock()

    charge_repo.get_by_id.return_value = charge
    payment_repo.get_total_paid_for_charge.return_value = Decimal("0")
    account_repo.get_by_id.return_value = AccountEntity(
        id=account_id,
        name="ООО Тест",
        owner_id=uuid4(),
        payment_details="СБП +7 900 000-00-00",
    )
    contract_repo.get_by_id.return_value = ContractEntity(
        id=charge.contract_id,
        account_id=account_id,
        property_id=uuid4(),
        tenant_id=uuid4(),
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=300),
        rent_amount=Decimal("50000"),
        payment_day=5,
        status="active",
    )
    prop = PropertyEntity(
        id=uuid4(),
        account_id=account_id,
        city="Москва",
        street="Тверская",
        house="1",
    )
    property_repo.get_by_id.return_value = prop
    tenant_repo.get_by_id.return_value = TenantEntity(
        id=uuid4(), account_id=account_id, full_name="Иван Петров"
    )
    doc = DocumentEntity(
        id=uuid4(),
        account_id=account_id,
        contract_id=charge.contract_id,
        filename="invoice.pdf",
        file_path="/tmp/invoice.pdf",
        category="invoice",
    )
    pdf_service.generate_and_save_invoice.return_value = doc
    invoice_repo.get_by_charge.return_value = None
    created = InvoiceEntity(
        id=uuid4(),
        account_id=account_id,
        contract_id=charge.contract_id,
        charge_id=charge.id,
        public_token="tok123",
        public_token_expires_at=_utc_now() + timedelta(days=90),
        document_id=None,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )
    invoice_repo.create.return_value = created

    def _update(entity):
        return entity

    invoice_repo.update.side_effect = _update

    svc = InvoiceService(
        invoice_repo,
        charge_repo,
        payment_repo,
        contract_repo,
        property_repo,
        tenant_repo,
        account_repo,
        document_repo,
        pdf_service,
    )
    svc._repos = {
        "invoice": invoice_repo,
        "charge": charge_repo,
        "doc": document_repo,
        "pdf": pdf_service,
    }
    return svc


class TestEnsureInvoice:
    def test_creates_stable_token_on_second_call(self, service, charge, account_id):
        first = service.ensure_invoice(charge.id, account_id)
        assert first.public_token == "tok123"
        assert first.document_id is not None

        existing = InvoiceEntity(
            id=first.invoice_id,
            account_id=account_id,
            contract_id=charge.contract_id,
            charge_id=charge.id,
            public_token="tok123",
            public_token_expires_at=_utc_now() + timedelta(days=90),
            document_id=first.document_id,
        )
        service.invoice_repo.get_by_charge.return_value = existing
        service.invoice_repo.create.reset_mock()

        second = service.ensure_invoice(charge.id, account_id)
        assert second.public_token == "tok123"
        service.invoice_repo.create.assert_not_called()

    def test_expired_token_is_renewed_when_invoice_is_refreshed(
        self, service, charge, account_id
    ):
        existing = InvoiceEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=charge.contract_id,
            charge_id=charge.id,
            public_token="expired-token",
            public_token_expires_at=_utc_now() - timedelta(seconds=1),
        )
        service.invoice_repo.get_by_charge.return_value = existing

        refreshed = service.ensure_invoice(charge.id, account_id)

        assert refreshed.public_token != "expired-token"
        assert refreshed.public_token_expires_at > _utc_now()

    def test_get_by_charge_404(self, service, account_id):
        service.invoice_repo.get_by_charge.return_value = None
        with pytest.raises(NotFoundError):
            service.get_by_charge(uuid4(), account_id)

    def test_public_payload(self, service, charge, account_id):
        invoice = InvoiceEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=charge.contract_id,
            charge_id=charge.id,
            public_token="pubtok",
            public_token_expires_at=_utc_now() + timedelta(days=90),
            document_id=None,
        )
        service.invoice_repo.get_by_token.return_value = invoice
        dto = service.get_public("pubtok")
        assert dto.landlord_name == "ООО Тест"
        assert dto.tenant_name == "Иван Петров"
        assert dto.amount == Decimal("50000")
        assert dto.amount_remaining == Decimal("50000")
        assert dto.payment_details == "СБП +7 900 000-00-00"
        assert "Тверская" in dto.property_address
