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
    password_reset_token_id: UUID | None = None
    
@dataclass
class AccountEntity:
    """Аккаунт (тенант) для multi-tenancy изоляции."""
    
    id: UUID
    name: str
    owner_id: UUID
    base_currency: str = "RUB"
    timezone: str = "Europe/Moscow"
    payment_details: str | None = None
    plan: str = "free"
    subscription_status: str = "none"
    subscription_period_end: datetime | None = None
    yookassa_payment_method_id: str | None = None
    yookassa_last_payment_id: str | None = None
    yookassa_renewal_period_end: datetime | None = None
    yookassa_renewal_started_at: datetime | None = None
    yookassa_renewal_idempotence_key: str | None = None
    yookassa_renewal_payment_id: str | None = None
    yookassa_renewal_status: str | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class MembershipEntity:
    """Участник аккаунта (связь user ↔ account с ролью)."""

    id: UUID
    account_id: UUID
    user_id: UUID
    role: str
    is_active: bool = True
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class AuthSessionEntity:
    """Отдельная авторизационная сессия пользователя."""

    id: UUID
    user_id: UUID
    account_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None
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
    portal_token: str | None = None
    portal_token_expires_at: datetime | None = None
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
    receipt_id: UUID | None = None
    allocation_event_id: UUID | None = None


@dataclass
class PaymentReceiptEntity:
    """Неизменяемый исходный факт поступления денег."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    date_paid: date
    original_amount: Decimal
    currency: str
    method: str
    source: str = "manual"
    note: str | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class PaymentReceiptEventEntity:
    """Корректировка или отмена части исходного поступления."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    receipt_id: UUID
    event_type: str
    amount_delta: Decimal
    resulting_date_paid: date
    resulting_method: str
    resulting_note: str | None = None
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class PaymentAllocationEventEntity:
    """Добавление или компенсация распределения receipt на начисление."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    receipt_id: UUID
    rent_charge_id: UUID
    event_type: str
    amount: Decimal
    reverses_event_id: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)


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
    source_id: UUID | None = None
    created_at: datetime | None = None
    
@dataclass
class InvoiceEntity:
    """Квитанция (инвойс) по начислению — публичная ссылка + PDF."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    charge_id: UUID
    public_token: str
    public_token_expires_at: datetime
    document_id: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


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
    """Сохранённый документ или вложение."""

    id: UUID
    account_id: UUID
    filename: str
    file_path: str
    contract_id: UUID | None = None
    property_id: UUID | None = None
    title: str | None = None
    category: str = "other"
    mime_type: str = "application/pdf"
    size_bytes: int | None = None
    source: str = "generated"
    created_at: datetime = field(default_factory=_utc_now)


@dataclass
class ContractTemplateEntity:
    """Шаблон договора с плейсхолдерами."""

    id: UUID
    account_id: UUID
    name: str
    title: str
    body: str
    property_type: str | None = None  # apartment|house|room|commercial|None=все
    is_default: bool = False
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)

@dataclass
class NotificationDismissalEntity:
    """Скрытое пользователем уведомление (ключ inbox)."""

    id: UUID
    account_id: UUID
    user_id: UUID
    notification_key: str
    dismissed_at: datetime = field(default_factory=_utc_now)


@dataclass
class EmailDispatchLogEntity:
    """Лог отправленных email-уведомлений (дедуп)."""

    id: UUID
    account_id: UUID
    notification_key: str
    sent_at: datetime = field(default_factory=_utc_now)


@dataclass
class AccountInviteEntity:
    """Приглашение в аккаунт по ссылке."""

    id: UUID
    account_id: UUID
    email: str
    full_name: str
    role: str  # manager | accountant
    token: str
    expires_at: datetime
    invited_by_user_id: UUID
    accepted_at: datetime | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


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
    payment_receipt_id: UUID | None = None


@dataclass
class PaymentClaimEntity:
    """Заявка арендатора «я оплатил» (без записи в ledger)."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    status: str  # pending | dismissed | confirmed
    charge_id: UUID | None = None
    amount: Decimal | None = None
    note: str | None = None
    resolved_at: datetime | None = None
    resolved_by: UUID | None = None
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)


@dataclass
class OutboxMessageEntity:
    """Allow-listed команда фонового выполнения в PostgreSQL outbox."""

    id: UUID
    account_id: UUID
    contract_id: UUID
    task_name: str
    payload_version: int = 1
    status: str = "pending"
    attempts: int = 0
    task_failures: int = 0
    created_at: datetime = field(default_factory=_utc_now)
    available_at: datetime = field(default_factory=_utc_now)
    lease_until: datetime | None = None
    lease_token: UUID | None = None
    published_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    last_error: str | None = None
