"""Сервис публичного портала арендатора и заявок «я оплатил»."""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import ContractEntity, ContractEventEntity, PaymentClaimEntity
from app.domain.interfaces import (
    IAccountRepository,
    IContractEventRepository,
    IContractRepository,
    IInvoiceRepository,
    IPaymentClaimRepository,
    IPaymentRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import compute_charge_status
from app.services.contract_event_labels import format_money
from app.services.dto.payment_dto import PaymentCreateDTO
from app.services.dto.portal_dto import (
    CreatePaymentClaimDTO,
    PortalClaimDTO,
    PortalHistoryLineDTO,
    PortalLinkDTO,
    PortalOpenChargeDTO,
    PublicPortalDTO,
)
from app.services.invoice_service import InvoiceService
from app.services.ledger_service import LedgerService
from app.services.payment_service import PaymentService

PORTAL_TOKEN_TTL = timedelta(hours=2)


class TenantPortalService:
    """Magic link портала договора: баланс, история, claim."""

    def __init__(
        self,
        contract_repo: IContractRepository,
        claim_repo: IPaymentClaimRepository,
        event_repo: IContractEventRepository,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
        account_repo: IAccountRepository,
        invoice_repo: IInvoiceRepository,
        ledger_service: LedgerService,
        invoice_service: InvoiceService,
        payment_service: PaymentService,
    ) -> None:
        self.contract_repo = contract_repo
        self.claim_repo = claim_repo
        self.event_repo = event_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.account_repo = account_repo
        self.invoice_repo = invoice_repo
        self.ledger_service = ledger_service
        self.invoice_service = invoice_service
        self.payment_service = payment_service

    def _share_url(self, token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/t/{token}"

    def _to_claim_dto(self, claim: PaymentClaimEntity) -> PortalClaimDTO:
        return PortalClaimDTO(
            id=claim.id,
            contract_id=claim.contract_id,
            charge_id=claim.charge_id,
            amount=claim.amount,
            note=claim.note,
            status=claim.status,
            created_at=claim.created_at,
            resolved_at=claim.resolved_at,
        )

    def ensure_portal(self, contract_id: UUID, account_id: UUID) -> PortalLinkDTO:
        """Создать или вернуть существующий portal_token."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        if not contract.portal_token or self._portal_token_expired(contract):
            contract.portal_token = secrets.token_urlsafe(32)
            contract.portal_token_expires_at = self._new_token_expiration()
            contract = self.contract_repo.update(contract)

        assert contract.portal_token is not None
        assert contract.portal_token_expires_at is not None
        return PortalLinkDTO(
            portal_token=contract.portal_token,
            share_url=self._share_url(contract.portal_token),
            portal_token_expires_at=contract.portal_token_expires_at,
        )

    def rotate_portal(self, contract_id: UUID, account_id: UUID) -> PortalLinkDTO:
        """Выпустить новый токен (старая ссылка перестаёт работать)."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        contract.portal_token = secrets.token_urlsafe(32)
        contract.portal_token_expires_at = self._new_token_expiration()
        contract = self.contract_repo.update(contract)
        assert contract.portal_token is not None
        assert contract.portal_token_expires_at is not None
        return PortalLinkDTO(
            portal_token=contract.portal_token,
            share_url=self._share_url(contract.portal_token),
            portal_token_expires_at=contract.portal_token_expires_at,
        )

    @staticmethod
    def _new_token_expiration() -> datetime:
        return datetime.now(timezone.utc) + PORTAL_TOKEN_TTL

    @staticmethod
    def _portal_token_expired(contract: ContractEntity) -> bool:
        expires_at = contract.portal_token_expires_at
        if expires_at is None:
            return True
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    def _resolve_contract_by_token(self, token: str):
        contract = self.contract_repo.get_by_portal_token(token)
        if not contract:
            raise NotFoundError("Portal link not found")
        return contract

    def get_public(self, token: str) -> PublicPortalDTO:
        """Публичные данные портала по magic link."""
        contract = self._resolve_contract_by_token(token)
        account_id = contract.account_id

        account = self.account_repo.get_by_id(account_id)
        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
        if not account or not prop or not tenant:
            raise NotFoundError("Portal data incomplete")

        ledger = self.ledger_service.get_ledger(contract.id, account_id)
        history = [
            PortalHistoryLineDTO(
                date=line.date,
                type=line.type,
                description=line.description,
                amount=line.amount,
                balance=line.balance,
            )
            for line in ledger.lines
        ]

        open_charges: list[PortalOpenChargeDTO] = []
        charges = self.charge_repo.list_by_contract(contract.id, account_id)
        for charge in charges:
            paid = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
            remaining = max(Decimal("0"), charge.amount - paid)
            if remaining <= 0:
                continue
            status = compute_charge_status(charge.amount, paid, charge.due_date)
            invoice_url = self.invoice_service.get_share_url_for_charge(
                charge.id, account_id
            )
            if not invoice_url:
                invoice = self.invoice_service.ensure_invoice(charge.id, account_id)
                invoice_url = invoice.share_url
            open_charges.append(
                PortalOpenChargeDTO(
                    charge_id=charge.id,
                    period_start=charge.period_start,
                    period_end=charge.period_end,
                    due_date=charge.due_date,
                    amount=charge.amount,
                    amount_paid=paid,
                    amount_remaining=remaining,
                    currency=charge.currency,
                    status=status,
                    invoice_url=invoice_url,
                )
            )
        open_charges.sort(key=lambda c: c.due_date)

        pending = self.claim_repo.get_pending_by_contract(contract.id, account_id)

        return PublicPortalDTO(
            landlord_name=account.name,
            property_address=prop.get_address(),
            tenant_name=tenant.full_name,
            currency=contract.currency,
            outstanding_balance=ledger.outstanding_balance,
            total_expected=ledger.total_expected,
            total_paid=ledger.total_paid,
            payment_details=account.payment_details,
            history=history,
            open_charges=open_charges,
            pending_claim=self._to_claim_dto(pending) if pending else None,
        )

    def create_claim(self, token: str, dto: CreatePaymentClaimDTO) -> PortalClaimDTO:
        """Создать заявку «я оплатил» по portal magic link."""
        contract = self._resolve_contract_by_token(token)
        return self._create_claim(contract, dto, require_amount=True)

    def create_claim_from_invoice(
        self, invoice_token: str, dto: CreatePaymentClaimDTO
    ) -> PortalClaimDTO:
        """Создать заявку «я оплатил» со страницы квитанции."""
        invoice = self.invoice_repo.get_by_token(invoice_token)
        if not invoice:
            raise NotFoundError("Invoice not found")

        contract = self.contract_repo.get_by_id(invoice.contract_id, invoice.account_id)
        if not contract:
            raise NotFoundError("Contract not found")

        charge_id = dto.charge_id or invoice.charge_id
        amount = dto.amount
        if amount is None:
            paid = self.payment_repo.get_total_paid_for_charge(
                invoice.charge_id, invoice.account_id
            )
            charge = self.charge_repo.get_by_id(invoice.charge_id, invoice.account_id)
            if not charge:
                raise NotFoundError("Charge not found")
            amount = max(Decimal("0"), charge.amount - paid)

        return self._create_claim(
            contract,
            CreatePaymentClaimDTO(charge_id=charge_id, amount=amount, note=dto.note),
            require_amount=True,
        )

    def _create_claim(
        self,
        contract: ContractEntity,
        dto: CreatePaymentClaimDTO,
        *,
        require_amount: bool,
    ) -> PortalClaimDTO:
        """Создать заявку (не трогает ledger)."""
        account_id = contract.account_id

        existing = self.claim_repo.get_pending_by_contract(contract.id, account_id)
        if existing:
            raise ConflictError("По этому договору уже есть необработанная заявка об оплате")

        charge_id = dto.charge_id
        if charge_id is not None:
            charge = self.charge_repo.get_by_id(charge_id, account_id)
            if not charge or charge.contract_id != contract.id:
                raise ValidationError("Начисление не принадлежит этому договору")

        amount = dto.amount
        if require_amount and amount is None:
            raise ValidationError("Укажите сумму оплаты")
        if amount is not None and amount <= 0:
            raise ValidationError("Сумма должна быть больше нуля")

        note = dto.note.strip() if dto.note else None
        if note == "":
            note = None

        claim = self.claim_repo.create(
            PaymentClaimEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract.id,
                charge_id=charge_id,
                amount=amount,
                note=note,
                status="pending",
            )
        )

        money_part = format_money(
            amount
            if amount is not None
            else max(
                Decimal("0"),
                self.ledger_service.get_ledger(contract.id, account_id).outstanding_balance,
            ),
            contract.currency,
        )
        self.event_repo.create(
            ContractEventEntity(
                id=uuid4(),
                account_id=account_id,
                contract_id=contract.id,
                event_type="payment_claim",
                title=f"Арендатор сообщил об оплате: {money_part}",
                description=note,
                event_metadata={
                    "claim_id": str(claim.id),
                    "amount": str(amount) if amount is not None else None,
                    "charge_id": str(charge_id) if charge_id else None,
                },
            )
        )

        return self._to_claim_dto(claim)

    def list_claims(
        self,
        contract_id: UUID,
        account_id: UUID,
        status: str | None = None,
    ) -> list[PortalClaimDTO]:
        """Список заявок по договору (CRM)."""
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")
        claims = self.claim_repo.list_by_contract(contract_id, account_id, status=status)
        return [self._to_claim_dto(c) for c in claims]

    def confirm_claim(
        self, claim_id: UUID, account_id: UUID, user_id: UUID
    ) -> PortalClaimDTO:
        """Подтвердить заявку: создать payment в ledger и закрыть claim."""
        claim = self.claim_repo.get_by_id(claim_id, account_id)
        if not claim:
            raise NotFoundError(f"Payment claim with id={claim_id} not found")
        if claim.status != "pending":
            raise ConflictError("Заявка уже обработана")
        if claim.amount is None or claim.amount <= 0:
            raise ValidationError("У заявки нет суммы — нельзя провести платёж")

        note = "Подтверждение заявки арендатора"
        if claim.note:
            note = f"{note}: {claim.note}"

        self.payment_service.create_payment(
            account_id,
            PaymentCreateDTO(
                contract_id=claim.contract_id,
                rent_charge_id=claim.charge_id,
                date_paid=date.today(),
                amount=claim.amount,
                method="transfer",
                note=note,
            ),
        )
        return self._resolve_claim(claim, user_id, "confirmed")

    def dismiss_claim(
        self, claim_id: UUID, account_id: UUID, user_id: UUID
    ) -> PortalClaimDTO:
        """Отклонить заявку без создания payment."""
        claim = self.claim_repo.get_by_id(claim_id, account_id)
        if not claim:
            raise NotFoundError(f"Payment claim with id={claim_id} not found")
        if claim.status != "pending":
            raise ConflictError("Заявка уже обработана")
        return self._resolve_claim(claim, user_id, "dismissed")

    def _resolve_claim(
        self,
        claim: PaymentClaimEntity,
        user_id: UUID,
        new_status: str,
    ) -> PortalClaimDTO:
        claim.status = new_status
        claim.resolved_at = datetime.now(timezone.utc)
        claim.resolved_by = user_id
        claim = self.claim_repo.update(claim)
        return self._to_claim_dto(claim)
