"""Зависимости FastAPI."""

from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_access_token

# Репозитории
from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository

# Сервисы
from app.services.contract_service import ContractService
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from app.services.property_service import PropertyService
from app.services.rent_charge_service import RentChargeService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService
from app.services.pdf_service import PdfService
from app.db.repositories.contract_event_repo import ContractEventRepository

from app.db.session import get_db_session


# ==================== БАЗОВЫЕ ====================

def get_user_repo(session: Session = Depends(get_db_session)) -> UserRepository:
    return UserRepository(session)

def get_account_repo(session: Session = Depends(get_db_session)) -> AccountRepository:
    return AccountRepository(session)

def get_property_repo(session: Session = Depends(get_db_session)) -> PropertyRepository:
    return PropertyRepository(session)

def get_tenant_repo(session: Session = Depends(get_db_session)) -> TenantRepository:
    return TenantRepository(session)

def get_contract_repo(session: Session = Depends(get_db_session)) -> ContractRepository:
    return ContractRepository(session)

def get_rent_charge_repo(session: Session = Depends(get_db_session)) -> RentChargeRepository:
    return RentChargeRepository(session)

def get_payment_repo(session: Session = Depends(get_db_session)) -> PaymentRepository:
    return PaymentRepository(session)


# ==================== СЕРВИСЫ ====================

def get_user_service(
    user_repo: UserRepository = Depends(get_user_repo),
    account_repo: AccountRepository = Depends(get_account_repo),
) -> UserService:
    return UserService(user_repo, account_repo)

def get_property_service(
    repo: PropertyRepository = Depends(get_property_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> PropertyService:
    return PropertyService(repo, contract_repo, tenant_repo)

def get_tenant_service(
    repo: TenantRepository = Depends(get_tenant_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
) -> TenantService:
    return TenantService(repo, contract_repo, property_repo)

def get_contract_service(
    repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    session: Session = Depends(get_db_session),
) -> ContractService:
    return ContractService(repo, charge_repo, payment_repo, session)

from app.db.repositories.reminder_repo import ReminderRepository
from app.services.reminder_service import ReminderService

def get_reminder_repo(session: Session = Depends(get_db_session)) -> ReminderRepository:
    return ReminderRepository(session)


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
    session=Depends(get_db_session),
) -> PaymentService:
    return PaymentService(payment_repo, contract_repo, charge_repo, session)

def get_dashboard_service(
    property_repo=Depends(get_property_repo),
    contract_repo=Depends(get_contract_repo),
    charge_repo=Depends(get_rent_charge_repo),
    payment_repo=Depends(get_payment_repo),
    tenant_repo=Depends(get_tenant_repo),
) -> DashboardService:
    return DashboardService(property_repo, contract_repo, charge_repo, payment_repo, tenant_repo)


# ==================== АУТЕНТИФИКАЦИЯ ====================

def _decode_token(authorization: str) -> dict:
    """Извлечь и декодировать JWT-токен из заголовка."""
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header")
    token = authorization.split(" ")[1]
    try:
        return decode_access_token(token)
    except Exception as e:
        raise UnauthorizedError("Invalid token") from e


def get_current_user_id(authorization: str = Header(...)) -> UUID:
    """Получить ID текущего пользователя из JWT-токена."""
    return UUID(_decode_token(authorization)["sub"])


def get_current_account_id(authorization: str = Header(...)) -> UUID:
    """Получить ID аккаунта из JWT-токена."""
    return UUID(_decode_token(authorization)["account_id"])

from app.services.ledger_service import LedgerService


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
    session: Session = Depends(get_db_session),
) -> ReminderService:
    return ReminderService(reminder_repo, charge_repo, contract_repo, tenant_repo, session)

from app.services.credit_score_service import CreditScoreService

def get_credit_score_service(
    payment_repo: PaymentRepository = Depends(get_payment_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
) -> CreditScoreService:
    return CreditScoreService(payment_repo, charge_repo)

from app.services.roi_service import RoiService

def get_roi_service(
    property_repo: PropertyRepository = Depends(get_property_repo),
    contract_repo: ContractRepository = Depends(get_contract_repo),
    payment_repo: PaymentRepository = Depends(get_payment_repo),
) -> RoiService:
    return RoiService(property_repo, contract_repo, payment_repo)

from app.db.repositories.document_repo import DocumentRepository

def get_document_repo(session: Session = Depends(get_db_session)) -> DocumentRepository:
    return DocumentRepository(session)

def get_pdf_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    document_repo: DocumentRepository = Depends(get_document_repo),
) -> PdfService:
    return PdfService(contract_repo, property_repo, tenant_repo, document_repo)

def get_contract_event_repo(session: Session = Depends(get_db_session)) -> ContractEventRepository:
    return ContractEventRepository(session)

from app.services.forecast_service import ForecastService

def get_forecast_service(
    contract_repo: ContractRepository = Depends(get_contract_repo),
    charge_repo: RentChargeRepository = Depends(get_rent_charge_repo),
    property_repo: PropertyRepository = Depends(get_property_repo),
) -> ForecastService:
    return ForecastService(contract_repo, charge_repo, property_repo)