"""Unit-тесты портала арендатора и claims."""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import (
    ContractEntity,
    PaymentClaimEntity,
)
from app.services.dto.dashboard_dto import LedgerDTO
from app.services.dto.portal_dto import CreatePaymentClaimDTO
from app.services.tenant_portal_service import TenantPortalService


def _contract(account_id, portal_token=None):
    return ContractEntity(
        id=uuid4(),
        account_id=account_id,
        property_id=uuid4(),
        tenant_id=uuid4(),
        start_date=date.today() - timedelta(days=30),
        end_date=date.today() + timedelta(days=300),
        rent_amount=Decimal("40000"),
        payment_day=1,
        status="active",
        portal_token=portal_token,
        portal_token_expires_at=(
            datetime.now(timezone.utc) + timedelta(hours=2)
            if portal_token
            else None
        ),
    )


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def service(account_id):
    contract_repo = Mock()
    claim_repo = Mock()
    event_repo = Mock()
    charge_repo = Mock()
    payment_repo = Mock()
    property_repo = Mock()
    tenant_repo = Mock()
    account_repo = Mock()
    invoice_repo = Mock()
    ledger_service = Mock()
    invoice_service = Mock()
    payment_service = Mock()

    svc = TenantPortalService(
        contract_repo,
        claim_repo,
        event_repo,
        charge_repo,
        payment_repo,
        property_repo,
        tenant_repo,
        account_repo,
        invoice_repo,
        ledger_service,
        invoice_service,
        payment_service,
    )
    return svc


class TestEnsurePortal:
    def test_creates_token(self, service, account_id):
        contract = _contract(account_id)
        service.contract_repo.get_by_id.return_value = contract
        service.contract_repo.update.side_effect = lambda c: c

        result = service.ensure_portal(contract.id, account_id)

        assert result.portal_token
        assert result.share_url.endswith(f"/t/{result.portal_token}")
        assert timedelta(hours=1, minutes=55) < (
            result.portal_token_expires_at - datetime.now(timezone.utc)
        )
        service.contract_repo.update.assert_called_once()

    def test_reuses_token(self, service, account_id):
        contract = _contract(account_id, portal_token="existing-token")
        service.contract_repo.get_by_id.return_value = contract

        result = service.ensure_portal(contract.id, account_id)

        assert result.portal_token == "existing-token"
        service.contract_repo.update.assert_not_called()

    def test_renews_expired_token(self, service, account_id):
        contract = _contract(account_id, portal_token="expired-token")
        contract.portal_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        service.contract_repo.get_by_id.return_value = contract
        service.contract_repo.update.side_effect = lambda entity: entity

        result = service.ensure_portal(contract.id, account_id)

        assert result.portal_token != "expired-token"
        assert timedelta(hours=1, minutes=55) < (
            result.portal_token_expires_at - datetime.now(timezone.utc)
        )
        service.contract_repo.update.assert_called_once()


class TestCreateClaim:
    def test_creates_claim_and_event(self, service, account_id):
        contract = _contract(account_id, portal_token="tok")
        service.contract_repo.get_by_portal_token.return_value = contract
        service.claim_repo.get_pending_by_contract.return_value = None
        service.ledger_service.get_ledger.return_value = LedgerDTO(
            total_expected=Decimal("40000"),
            total_paid=Decimal("0"),
            outstanding_balance=Decimal("40000"),
            lines=[],
        )
        created = PaymentClaimEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract.id,
            status="pending",
            amount=Decimal("40000"),
        )
        service.claim_repo.create.return_value = created

        result = service.create_claim(
            "tok",
            CreatePaymentClaimDTO(amount=Decimal("40000"), note="Перевёл"),
        )

        assert result.status == "pending"
        service.claim_repo.create.assert_called_once()
        service.event_repo.create.assert_called_once()
        event = service.event_repo.create.call_args[0][0]
        assert event.event_type == "payment_claim"

    def test_rejects_second_pending(self, service, account_id):
        contract = _contract(account_id, portal_token="tok")
        service.contract_repo.get_by_portal_token.return_value = contract
        service.claim_repo.get_pending_by_contract.return_value = PaymentClaimEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract.id,
            status="pending",
        )

        with pytest.raises(ConflictError):
            service.create_claim("tok", CreatePaymentClaimDTO(amount=Decimal("1000")))

    def test_requires_amount(self, service, account_id):
        contract = _contract(account_id, portal_token="tok")
        service.contract_repo.get_by_portal_token.return_value = contract
        service.claim_repo.get_pending_by_contract.return_value = None

        with pytest.raises(ValidationError):
            service.create_claim("tok", CreatePaymentClaimDTO())

    def test_invalid_charge(self, service, account_id):
        contract = _contract(account_id, portal_token="tok")
        service.contract_repo.get_by_portal_token.return_value = contract
        service.claim_repo.get_pending_by_contract.return_value = None
        service.charge_repo.get_by_id.return_value = None

        with pytest.raises(ValidationError):
            service.create_claim(
                "tok",
                CreatePaymentClaimDTO(charge_id=uuid4(), amount=Decimal("1000")),
            )


class TestResolveClaim:
    def test_dismiss(self, service, account_id):
        claim = PaymentClaimEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=uuid4(),
            status="pending",
        )
        service.claim_repo.get_by_id.return_value = claim
        service.claim_repo.update.side_effect = lambda c: c
        user_id = uuid4()

        result = service.dismiss_claim(claim.id, account_id, user_id)

        assert result.status == "dismissed"
        assert result.resolved_at is not None
        service.payment_service.create_payment.assert_not_called()

    def test_confirm_creates_payment(self, service, account_id):
        contract_id = uuid4()
        charge_id = uuid4()
        claim = PaymentClaimEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=contract_id,
            charge_id=charge_id,
            amount=Decimal("35000"),
            status="pending",
            note="Перевёл",
        )
        service.claim_repo.get_by_id.return_value = claim
        service.claim_repo.update.side_effect = lambda c: c

        result = service.confirm_claim(claim.id, account_id, uuid4())

        assert result.status == "confirmed"
        service.payment_service.create_payment.assert_called_once()
        dto = service.payment_service.create_payment.call_args[0][1]
        assert dto.contract_id == contract_id
        assert dto.rent_charge_id == charge_id
        assert dto.amount == Decimal("35000")

    def test_already_resolved(self, service, account_id):
        claim = PaymentClaimEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=uuid4(),
            status="confirmed",
            resolved_at=datetime.now(timezone.utc),
        )
        service.claim_repo.get_by_id.return_value = claim

        with pytest.raises(ConflictError):
            service.confirm_claim(claim.id, account_id, uuid4())

    def test_public_404(self, service):
        service.contract_repo.get_by_portal_token.return_value = None
        with pytest.raises(NotFoundError):
            service.get_public("missing")
