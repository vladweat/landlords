"""Сервис квитанций (инвойсов) по начислениям."""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.domain.entities import InvoiceEntity
from app.domain.interfaces import (
    IAccountRepository,
    IContractRepository,
    IDocumentRepository,
    IInvoiceRepository,
    IPaymentClaimRepository,
    IPaymentRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import compute_charge_status
from app.services.document_service import document_file_path
from app.services.dto.invoice_dto import InvoiceDTO, PublicInvoiceDTO
from app.services.pdf_service import PdfService

PUBLIC_INVOICE_TOKEN_TTL_DAYS = 90


class InvoiceService:
    """Создание и публичный просмотр квитанций."""

    def __init__(
        self,
        invoice_repo: IInvoiceRepository,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
        account_repo: IAccountRepository,
        document_repo: IDocumentRepository,
        pdf_service: PdfService,
        claim_repo: IPaymentClaimRepository | None = None,
    ) -> None:
        self.invoice_repo = invoice_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.account_repo = account_repo
        self.document_repo = document_repo
        self.pdf_service = pdf_service
        self.claim_repo = claim_repo

    def _share_url(self, token: str) -> str:
        base = settings.FRONTEND_URL.rstrip("/")
        return f"{base}/i/{token}"

    def _to_dto(self, invoice: InvoiceEntity) -> InvoiceDTO:
        return InvoiceDTO(
            invoice_id=invoice.id,
            charge_id=invoice.charge_id,
            contract_id=invoice.contract_id,
            document_id=invoice.document_id,
            share_url=self._share_url(invoice.public_token),
            public_token=invoice.public_token,
            public_token_expires_at=invoice.public_token_expires_at,
        )

    def get_by_charge(self, charge_id: UUID, account_id: UUID) -> InvoiceDTO:
        """Получить существующую квитанцию по начислению."""
        invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice:
            raise NotFoundError("Invoice not found")
        return self._to_dto(invoice)

    def get_share_url_for_charge(self, charge_id: UUID, account_id: UUID) -> str | None:
        """URL публичной квитанции, если она уже создана."""
        invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice or self._public_token_expired(invoice):
            return None
        return self._share_url(invoice.public_token)

    def ensure_invoice(self, charge_id: UUID, account_id: UUID) -> InvoiceDTO:
        """Создать или обновить квитанцию и перегенерировать PDF."""
        charge = self.charge_repo.get_by_id(charge_id, account_id)
        if not charge:
            raise NotFoundError(f"Charge {charge_id} not found")

        invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice:
            invoice = self.invoice_repo.create(
                InvoiceEntity(
                    id=uuid4(),
                    account_id=account_id,
                    contract_id=charge.contract_id,
                    charge_id=charge_id,
                    public_token=secrets.token_urlsafe(32),
                    public_token_expires_at=self._new_token_expiration(),
                )
            )
        elif self._public_token_expired(invoice):
            invoice.public_token = secrets.token_urlsafe(32)
            invoice.public_token_expires_at = self._new_token_expiration()

        amount_paid = self.payment_repo.get_total_paid_for_charge(charge_id, account_id)
        status = compute_charge_status(charge.amount, amount_paid, charge.due_date)
        remaining = max(Decimal("0"), charge.amount - amount_paid)

        account = self.account_repo.get_by_id(account_id)
        contract = self.contract_repo.get_by_id(charge.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract {charge.contract_id} not found")
        prop = self.property_repo.get_by_id(contract.property_id, account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)

        doc = self.pdf_service.generate_and_save_invoice(
            contract_id=charge.contract_id,
            account_id=account_id,
            landlord_name=account.name if account else "Арендодатель",
            tenant_name=tenant.full_name if tenant else "Арендатор",
            property_address=prop.get_address() if prop else "",
            period_start=charge.period_start,
            period_end=charge.period_end,
            due_date=charge.due_date,
            amount=charge.amount,
            amount_paid=amount_paid,
            amount_remaining=remaining,
            currency=charge.currency,
            status=status,
            payment_details=account.payment_details if account else None,
        )

        invoice.document_id = doc.id
        invoice = self.invoice_repo.update(invoice)
        return self._to_dto(invoice)

    def rotate_public_link(self, charge_id: UUID, account_id: UUID) -> InvoiceDTO:
        """Перевыпустить capability URL, немедленно отключив прежний токен."""
        charge = self.charge_repo.get_by_id(charge_id, account_id)
        if not charge:
            raise NotFoundError(f"Charge {charge_id} not found")

        invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice:
            self.ensure_invoice(charge_id, account_id)
            invoice = self.invoice_repo.get_by_charge(charge_id, account_id)
        if not invoice:
            raise NotFoundError("Invoice not found")

        invoice.public_token = secrets.token_urlsafe(32)
        invoice.public_token_expires_at = self._new_token_expiration()
        return self._to_dto(self.invoice_repo.update(invoice))

    @staticmethod
    def _new_token_expiration() -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=PUBLIC_INVOICE_TOKEN_TTL_DAYS)

    @staticmethod
    def _public_token_expired(invoice: InvoiceEntity) -> bool:
        expires_at = invoice.public_token_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return expires_at <= datetime.now(timezone.utc)

    def get_public(self, token: str) -> PublicInvoiceDTO:
        """Публичные данные квитанции по токену."""
        invoice = self.invoice_repo.get_by_token(token)
        if not invoice:
            raise NotFoundError("Invoice not found")

        charge = self.charge_repo.get_by_id(invoice.charge_id, invoice.account_id)
        if not charge:
            raise NotFoundError("Charge not found")

        amount_paid = self.payment_repo.get_total_paid_for_charge(
            invoice.charge_id, invoice.account_id
        )
        status = compute_charge_status(charge.amount, amount_paid, charge.due_date)
        remaining = max(Decimal("0"), charge.amount - amount_paid)

        account = self.account_repo.get_by_id(invoice.account_id)
        contract = self.contract_repo.get_by_id(invoice.contract_id, invoice.account_id)
        if not contract:
            raise NotFoundError("Contract not found")
        prop = self.property_repo.get_by_id(contract.property_id, invoice.account_id)
        tenant = self.tenant_repo.get_by_id(contract.tenant_id, invoice.account_id)

        filename = None
        if invoice.document_id:
            doc = self.document_repo.get_by_id(invoice.document_id, invoice.account_id)
            if doc:
                filename = doc.filename

        has_pending_claim = False
        if self.claim_repo is not None:
            pending = self.claim_repo.get_pending_by_contract(
                invoice.contract_id, invoice.account_id
            )
            has_pending_claim = pending is not None

        return PublicInvoiceDTO(
            landlord_name=account.name if account else "Арендодатель",
            property_address=prop.get_address() if prop else "",
            tenant_name=tenant.full_name if tenant else "Арендатор",
            period_start=charge.period_start,
            period_end=charge.period_end,
            due_date=charge.due_date,
            amount=charge.amount,
            amount_paid=amount_paid,
            amount_remaining=remaining,
            currency=charge.currency,
            status=status,
            payment_details=account.payment_details if account else None,
            filename=filename,
            has_pending_claim=has_pending_claim,
        )

    def get_public_pdf_bytes(self, token: str) -> tuple[bytes, str]:
        """Вернуть существующий PDF по публичному токену без побочных записей."""
        invoice = self.invoice_repo.get_by_token(token)
        if not invoice:
            raise NotFoundError("Invoice not found")

        if not invoice.document_id:
            raise NotFoundError("Invoice PDF not available")
        doc = self.document_repo.get_by_id(invoice.document_id, invoice.account_id)
        if not doc:
            raise NotFoundError("Invoice PDF not available")
        with open(document_file_path(doc, invoice.account_id), "rb") as f:
            return f.read(), doc.filename
