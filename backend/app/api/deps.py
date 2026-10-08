"""Зависимости FastAPI."""

from typing import Annotated
from uuid import UUID

from fastapi import Cookie, Header

from app.core.config import settings
from app.core.cookies import ACCESS_TOKEN_COOKIE
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.repositories.account_invite_repo import AccountInviteRepository
from app.domain.billing import is_subscription_write_blocked
from app.domain.permissions import Permission as Perm

# Репозитории
from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_event_repo import ContractEventRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.contract_template_repo import ContractTemplateRepository
from app.db.repositories.document_repo import DocumentRepository
from app.db.repositories.email_dispatch_log_repo import EmailDispatchLogRepository
from app.db.repositories.feedback_repo import FeedbackRepository
from app.db.repositories.invoice_repo import InvoiceRepository
from app.db.repositories.membership_repo import MembershipRepository
from app.db.repositories.notification_dismissal_repo import (
    NotificationDismissalRepository,
)
from app.db.repositories.payment_claim_repo import PaymentClaimRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.property_expense_repo import PropertyExpenseRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.reminder_repo import ReminderRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import get_db_session
from app.domain.entities import MembershipEntity
from app.domain.permissions import Permission, has_permission

# Сервисы
from app.services.account_export_service import AccountExportService
from app.services.account_service import AccountService
from app.services.audit_log_service import AuditService
from app.services.billing_service import BillingService
from app.services.calendar_service import CalendarService
from app.services.contract_event_service import ContractEventService
from app.services.contract_service import ContractService
from app.services.contract_template_service import ContractTemplateService
from app.services.credit_score_service import CreditScoreService
from app.services.dashboard_service import DashboardService
from app.services.document_service import DocumentService
from app.services.email_service import EmailService
from app.services.feedback_service import FeedbackService
from app.services.status_service import StatusService
from app.services.yookassa_client import YooKassaClient
from app.services.forecast_service import ForecastService
from app.services.invite_service import InviteService
from app.services.invoice_service import InvoiceService
from app.services.ledger_service import LedgerService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.services.pdf_service import PdfService
from app.services.plan_limit_service import PlanLimitService
from app.services.property_expense_service import PropertyExpenseService
from app.services.property_service import PropertyService
from app.services.reminder_service import ReminderService
from app.services.rent_charge_service import RentChargeService
from app.services.report_export_service import ReportExportService
from app.services.roi_service import RoiService
from app.services.tenant_portal_service import TenantPortalService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService
from fastapi import Depends, Header
from sqlalchemy.orm import Session


def get_email_service() -> EmailService:
    return EmailService()


# ==================== БАЗОВЫЕ ====================

def get_user_repo(session: Session = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)

def get_account_repo(session: Session = Depends(get_db_session)) -> AccountRepository:
    return AccountRepository(session)

def get_membership_repo(session: Session = Depends(get_db_session)) -> MembershipRepository:
    return MembershipRepository(session)

def get_property_repo(session: Session = Depends(get_db_session)) -> PropertyRepository:
    return PropertyRepository(session)

def get_tenant_repo(session: Session = Depends(get_db_session)) -> TenantRepository:
    return TenantRepository(session)

def get_contract_repo(session: Session = Depends(get_db_session)) -> ContractRepository:
    return ContractRepository(session)

def get_contract_template_repo(
    session: Session = Depends(get_db_session),
) -> ContractTemplateRepository:
    return ContractTemplateRepository(session)

def get_rent_charge_repo(session: Session = Depends(get_db_session)) -> RentChargeRepository:
    return RentChargeRepository(session)

def get_payment_repo(session: Session = Depends(get_db_session)) -> PaymentRepository:
    return PaymentRepository(session)

def get_property_expense_repo(
    session: Session = Depends(get_db_session),
) -> PropertyExpenseRepository:
    return PropertyExpenseRepository(session)

def get_reminder_repo(session: Session = Depends(get_db_session)) -> ReminderRepository:
    return ReminderRepository(session)

def get_document_repo(session: Session = Depends(get_db_session)) -> DocumentRepository:
    return DocumentRepository(session)

def get_contract_event_repo(session: Session = Depends(get_db_session)) -> ContractEventRepository:
    return ContractEventRepository(session)

def get_feedback_repo(session: Session = Depends(get_db_session)) -> FeedbackRepository:
    return FeedbackRepository(session)

def get_invoice_repo(session: Session = Depends(get_db_session)) -> InvoiceRepository:
    return InvoiceRepository(session)

def get_payment_claim_repo(
    session: Session = Depends(get_db_session),
) -> PaymentClaimRepository:
    return PaymentClaimRepository(session)

def get_notification_dismissal_repo(
    session: Session = Depends(get_db_session),
) -> NotificationDismissalRepository:
    return NotificationDismissalRepository(session)

def get_email_dispatch_log_repo(
    session: Session = Depends(get_db_session),
) -> EmailDispatchLogRepository:
    return EmailDispatchLogRepository(session)

def get_account_invite_repo(
    session: Session = Depends(get_db_session),
) -> AccountInviteRepository:
    return AccountInviteRepository(session)

def get_audit_service(session: Session = Depends(get_db_session)) -> AuditService:
    return AuditService(session)


# ==================== СЕРВИСЫ ====================

def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
    account_repo: AccountRepository = Depends(get_account_repo),
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    email_service: EmailService = Depends(get_email_service),
) -> UserService:
    return UserService(user_repo, account_repo, membership_repo, email_service)

def get_account_service(
    account_repo: AccountRepository = Depends(get_account_repo),
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> AccountService:
    return AccountService(account_repo, membership_repo, user_repo)


def get_account_export_service(
    account_repo: AccountRepository = Depends(get_account_repo),
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    expense_repo: PropertyExpenseRepository = Depends(get_property_expense_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
    feedback_repo: FeedbackRepository = Depends(get_feedback_repo),
) -> AccountExportService:
    return AccountExportService(
        account_repo,
        membership_repo,
        user_repo,
        property_repo,
        tenant_repo,
        contract_repo,
        charge_repo,
        payment_repo,
        expense_repo,
        document_repo,
        feedback_repo,
    )


def get_status_service() -> StatusService:
    return StatusService()


def get_plan_limit_service(
    account_repo: AccountRepository = Depends(get_account_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    invite_repo: AccountInviteRepository = Depends(get_account_invite_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> PlanLimitService:
    return PlanLimitService(
        account_repo, property_repo, membership_repo, invite_repo, document_repo
    )


def get_billing_service(
    account_repo: AccountRepository = Depends(get_account_repo),
) -> BillingService:
    return BillingService(account_repo, YooKassaClient())


def get_invite_service(
    invite_repo: AccountInviteRepository = Depends(get_account_invite_repo),
    account_repo: AccountRepository = Depends(get_account_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    email_service: EmailService = Depends(get_email_service),
    plan_limit_service: PlanLimitService = Depends(get_plan_limit_service),
) -> InviteService:
    return InviteService(
        invite_repo,
        account_repo,
        user_repo,
        membership_repo,
        email_service,
        plan_limit_service,
    )

def get_property_service(
    repo: PropertyRepository = Depends(get_property_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    plan_limit_service: PlanLimitService = Depends(get_plan_limit_service),
) -> PropertyService:
    return PropertyService(repo, contract_repo, tenant_repo, plan_limit_service)

def get_tenant_service(
    repo: TenantRepository = Depends(get_tenant_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
) -> TenantService:
    return TenantService(repo, contract_repo, property_repo)

def get_contract_template_service(
    template_repo: ContractTemplateRepository = Depends(get_contract_template_repo),
) -> ContractTemplateService:
    return ContractTemplateService(template_repo)

def get_pdf_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
    template_service: ContractTemplateService = Depends(get_contract_template_service),
    account_repo: AccountRepository = Depends(get_account_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    plan_limit_service: PlanLimitService = Depends(get_plan_limit_service),
) -> PdfService:
    return PdfService(
        contract_repo,
        property_repo,
        tenant_repo,
        document_repo,
        template_service,
        account_repo,
        user_repo,
        plan_limit_service,
    )


def get_document_service(
    document_repo: DocumentRepository = Depends(get_document_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    plan_limit_service: PlanLimitService = Depends(get_plan_limit_service),
) -> DocumentService:
    return DocumentService(
        document_repo, contract_repo, property_repo, plan_limit_service
    )


def get_contract_service(
    repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
    audit_service: AuditService = Depends(get_audit_service),
    pdf_service: PdfService = Depends(get_pdf_service),
) -> ContractService:
    return ContractService(
        repo, charge_repo, payment_repo, event_repo, audit_service, pdf_service
    )

def get_rent_charge_service(
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    reminder_repo: ReminderRepository = Depends(get_reminder_repo),
) -> RentChargeService:
    return RentChargeService(charge_repo, payment_repo, contract_repo, reminder_repo)

def get_payment_service(
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
) -> PaymentService:
    return PaymentService(payment_repo, contract_repo, charge_repo, event_repo)

def get_property_expense_service(
    expense_repo: PropertyExpenseRepository = Depends(get_property_expense_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
) -> PropertyExpenseService:
    return PropertyExpenseService(expense_repo, property_repo)

def get_dashboard_service(
    property_repo=Depends(get_property_repo),
    contract_repo=Depends(get_contract_repo),
    charge_repo=Depends(get_rent_charge_repo),
    payment_repo=Depends(get_payment_repo),
    tenant_repo=Depends(get_tenant_repo),
    expense_repo=Depends(get_property_expense_repo),
) -> DashboardService:
    return DashboardService(
        property_repo, contract_repo, charge_repo, payment_repo, tenant_repo, expense_repo
    )

def get_ledger_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    reminder_repo: ReminderRepository = Depends(get_reminder_repo),
) -> LedgerService:
    return LedgerService(contract_repo, charge_repo, payment_repo, reminder_repo)

def get_reminder_service(
    reminder_repo: ReminderRepository = Depends(get_reminder_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
    invoice_repo: InvoiceRepository = Depends(get_invoice_repo),
) -> ReminderService:
    return ReminderService(
        reminder_repo, charge_repo, contract_repo, tenant_repo, event_repo, invoice_repo
    )


def get_invoice_service(
    invoice_repo: InvoiceRepository = Depends(get_invoice_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    account_repo: AccountRepository = Depends(get_account_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
    pdf_service: PdfService = Depends(get_pdf_service),
    claim_repo: PaymentClaimRepository = Depends(get_payment_claim_repo),
) -> InvoiceService:
    return InvoiceService(
        invoice_repo,
        charge_repo,
        payment_repo,
        contract_repo,
        property_repo,
        tenant_repo,
        account_repo,
        document_repo,
        pdf_service,
        claim_repo,
    )


def get_tenant_portal_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    claim_repo: PaymentClaimRepository = Depends(get_payment_claim_repo),
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    account_repo: AccountRepository = Depends(get_account_repo),
    invoice_repo: InvoiceRepository = Depends(get_invoice_repo),
    ledger_service: LedgerService = Depends(get_ledger_service),
    invoice_service: InvoiceService = Depends(get_invoice_service),
    payment_service: PaymentService = Depends(get_payment_service),
) -> TenantPortalService:
    return TenantPortalService(
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

def get_credit_score_service(
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
) -> CreditScoreService:
    return CreditScoreService(payment_repo, charge_repo)

def get_roi_service(
    property_repo: PropertyRepository = Depends(get_property_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    expense_repo: PropertyExpenseRepository = Depends(get_property_expense_repo),
) -> RoiService:
    return RoiService(property_repo, contract_repo, payment_repo, expense_repo)

def get_forecast_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
) -> ForecastService:
    return ForecastService(contract_repo, charge_repo, property_repo)

def get_calendar_service(
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> CalendarService:
    return CalendarService(
        charge_repo, payment_repo, contract_repo, property_repo, tenant_repo
    )

def get_contract_event_service(
    event_repo: ContractEventRepository = Depends(get_contract_event_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
) -> ContractEventService:
    return ContractEventService(event_repo, contract_repo)

def get_feedback_service(
    feedback_repo: FeedbackRepository = Depends(get_feedback_repo),
    email_service: EmailService = Depends(get_email_service),
) -> FeedbackService:
    return FeedbackService(feedback_repo, email_service)

def get_notification_service(
    calendar_service: CalendarService = Depends(get_calendar_service),
    dismissal_repo: NotificationDismissalRepository = Depends(
        get_notification_dismissal_repo
    ),
) -> NotificationService:
    return NotificationService(calendar_service, dismissal_repo)

def get_report_export_service(
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    expense_repo: PropertyExpenseRepository = Depends(get_property_expense_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> ReportExportService:
    return ReportExportService(
        payment_repo,
        charge_repo,
        expense_repo,
        contract_repo,
        property_repo,
        tenant_repo,
    )


# ==================== АУТЕНТИФИКАЦИЯ ====================

def _token_from_request(authorization: str | None, cookie_token: str | None) -> str:
    """Bearer имеет приоритет, иначе HttpOnly-cookie."""
    if authorization:
        if not authorization.startswith("Bearer "):
            raise UnauthorizedError("Invalid authorization header")
        return authorization.split(" ", 1)[1]
    if cookie_token:
        return cookie_token
    raise UnauthorizedError("Not authenticated")


def _decode_token(token: str) -> dict:
    """Декодировать JWT."""
    try:
        return decode_access_token(token)
    except Exception as e:
        raise UnauthorizedError("Invalid token") from e


def get_current_membership(
    authorization: Annotated[str | None, Header()] = None,
    access_token: Annotated[str | None, Cookie(alias=ACCESS_TOKEN_COOKIE)] = None,
    membership_repo: MembershipRepository = Depends(get_membership_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> MembershipEntity:
    """Проверить JWT (заголовок или cookie) и активную membership; role берётся из БД."""
    payload = _decode_token(_token_from_request(authorization, access_token))
    try:
        user_id = UUID(payload["sub"])
        account_id = UUID(payload["account_id"])
    except (KeyError, ValueError, TypeError) as e:
        raise UnauthorizedError("Invalid token payload") from e

    user = user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User is inactive or not found")

    membership = membership_repo.get_by_user_and_account(user_id, account_id)
    if not membership or not membership.is_active:
        raise UnauthorizedError("No active account membership")

    return membership


def get_current_user_id(
    membership: MembershipEntity = Depends(get_current_membership),
) -> UUID:
    """Получить ID текущего пользователя из проверенной membership."""
    return membership.user_id


def get_current_account_id(
    membership: MembershipEntity = Depends(get_current_membership),
) -> UUID:
    """Получить ID аккаунта из проверенной membership."""
    return membership.account_id


_WRITE_PERMISSIONS = frozenset(
    {
        Perm.WRITE_PROPERTIES,
        Perm.WRITE_TENANTS,
        Perm.WRITE_CONTRACTS,
        Perm.WRITE_DOCUMENTS,
        Perm.WRITE_PAYMENTS,
        Perm.WRITE_CHARGES,
        Perm.WRITE_EXPENSES,
        Perm.WRITE_REMINDERS,
    }
)


def require_permissions(*permissions: Permission):
    """Dependency factory: проверить права текущей роли и биллинг write-block."""

    def _checker(
        membership: MembershipEntity = Depends(get_current_membership),
        account_repo: AccountRepository = Depends(get_account_repo),
    ) -> MembershipEntity:
        for perm in permissions:
            if not has_permission(membership.role, perm):
                raise ForbiddenError("Недостаточно прав для этого действия")
        needs_write = any(p in _WRITE_PERMISSIONS for p in permissions)
        if needs_write:
            account = account_repo.get_by_id(membership.account_id)
            if account and is_subscription_write_blocked(
                account, grace_days=settings.BILLING_GRACE_DAYS
            ):
                raise ForbiddenError(
                    "Подписка не оплачена: изменения недоступны. "
                    "Оплатите тариф Pro в настройках."
                )
        return membership

    return _checker
