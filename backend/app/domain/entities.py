from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserEntity:
    """Пользователь системы."""
    
    id: UUID
    email: str
    password_hash: str
    full_name: str
    phone: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    
@dataclass
class AccountEntity:
    """Аккаунт (тенант) для multi-tenancy изоляции."""
    
    id: UUID
    name: str
    owner_id: UUID
    base_currency: str = "RUB"
    timezone: str = "Europe/Moscow"
    created_at: datetime = field(default_factory=_utc_now)
    

from decimal import Decimal


@dataclass
class PropertyEntity:
    """Объект недвижимости."""

    id: UUID
    account_id: UUID
    city: str
    street: str
    house: str
    building: str | None = None
    apartment: str | None = None
    type: str = "apartment"
    size_m2: float = 0.0
    purchase_price: Decimal | None = None
    status: str = "active"
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

    def get_address(self) -> str:
        """Полный адрес одной строкой."""
        parts = [f"г. {self.city}", f"ул. {self.street}", f"д. {self.house}"]
        if self.building:
            parts.append(f"корп. {self.building}")
        if self.apartment:
            parts.append(f"кв. {self.apartment}")
        return ", ".join(parts)


@dataclass
class TenantEntity:
    """Арендатор."""

    id: UUID
    account_id: UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    
from datetime import date


@dataclass
class ContractEntity:
    """Контракт аренды — центральный агрегат."""

    id: UUID
    account_id: UUID
    property_id: UUID
    tenant_id: UUID
    start_date: date
    end_date: date
    rent_amount: Decimal
    currency: str = "RUB"
    billing_period: str = "monthly"
    payment_day: int = 1  # 1-28
    deposit_amount: Decimal | None = None
    auto_generate_charges: bool = False
    status: str = "draft"  # draft, active, ended, terminated, overdue
    termination_reason: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    
@dataclass
class RentChargeEntity:
    """Начисление арендной платы (ожидаемый платёж)."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    due_date: date
    period_start: date
    period_end: date
    amount: Decimal
    currency: str = "RUB"
    status: str = "pending"  # pending, partially_paid, paid, overdue
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass
class PaymentEntity:
    """Фактический платёж."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    rent_charge_id: UUID | None = None
    date_paid: date = field(default_factory=date.today)
    amount: Decimal = Decimal("0")
    currency: str = "RUB"
    method: str = "transfer"  # cash, bank, transfer
    note: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass
class PropertyExpenseEntity:
    """Расход по объекту недвижимости (ЖКХ, ремонт, налоги и т.п.)."""

    id: UUID
    account_id: UUID
    property_id: UUID
    category: str  # utilities, repair, tax, realtor_fee, other
    amount: Decimal
    date_incurred: date
    currency: str = "RUB"
    note: str | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass
class LedgerLine:
    """Строка в ledger — либо начисление, либо платёж."""

    date: date
    type: str  # "charge" или "payment"
    description: str
    amount: Decimal  # положительное для charge, отрицательное для payment
    balance: Decimal  # накопительный баланс
    reminder_status: dict | None = None
    
@dataclass
class ReminderEntity:
    """Напоминание о просрочке."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    charge_id: UUID
    reminder_type: str  # first, second, third
    message_text: str
    created_at: datetime = field(default_factory=_utc_now)
    
@dataclass
class DocumentEntity:
    """Сохранённый документ."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    filename: str
    file_path: str
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ContractTemplateEntity:
    """Шаблон договора."""

    id: UUID
    account_id: UUID
    name: str
    is_default: bool = False
    file_data: bytes | None = None
    created_at: datetime = field(default_factory=_utc_now)

@dataclass
class FeedbackEntity:
    id: UUID
    account_id: UUID
    user_id: UUID
    category: str  # bug, feature, question, other
    message: str
    status: str = "new"
    created_at: datetime = field(default_factory=_utc_now)
    
@dataclass
class ContractEventEntity:
    id: UUID
    account_id: UUID
    contract_id: UUID
    event_type: str
    title: str
    description: str | None = None
    event_metadata: dict | None = None  # ← переименовано
    created_by: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)