"""Абстрактные интерфейсы репозиториев."""

from abc import ABC, abstractmethod
from datetime import date, datetime
from decimal import Decimal
from typing import Sequence
from uuid import UUID

from app.domain.entities import (
    AccountEntity,
    AccountInviteEntity,
    AuthSessionEntity,
    ContractEntity,
    ContractEventEntity,
    ContractTemplateEntity,
    DocumentEntity,
    EmailDispatchLogEntity,
    FeedbackEntity,
    InvoiceEntity,
    MembershipEntity,
    NotificationDismissalEntity,
    OutboxMessageEntity,
    PaymentAllocationEventEntity,
    PaymentClaimEntity,
    PaymentEntity,
    PaymentReceiptEntity,
    PaymentReceiptEventEntity,
    PropertyEntity,
    PropertyExpenseEntity,
    ReminderEntity,
    RentChargeEntity,
    TenantEntity,
    UserEntity,
)
from app.domain.pagination import PaginatedResult


class IUserRepository(ABC):
    """Интерфейс репозитория пользователей."""

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> UserEntity | None:
        """Получить пользователя по ID."""
        ...

    @abstractmethod
    def get_by_email(self, email: str) -> UserEntity | None:
        """Получить пользователя по email."""
        ...

    @abstractmethod
    def create(self, entity: UserEntity) -> UserEntity:
        """Создать пользователя."""
        ...

    @abstractmethod
    def update(self, entity: UserEntity) -> UserEntity:
        """Обновить пользователя."""
        ...

    @abstractmethod
    def consume_password_reset_token(self, user_id: UUID, token_id: UUID) -> bool:
        """Атомарно погасить одноразовый токен сброса пароля."""
        ...

    @abstractmethod
    def delete(self, user_id: UUID) -> None:
        """Удалить пользователя."""
        ...


class IAccountRepository(ABC):
    """Интерфейс репозитория аккаунтов."""

    @abstractmethod
    def get_by_id(self, account_id: UUID) -> AccountEntity | None:
        """Получить аккаунт по ID."""
        ...

    @abstractmethod
    def get_by_id_for_update(self, account_id: UUID) -> AccountEntity | None:
        """Получить аккаунт с блокировкой строки."""
        ...

    @abstractmethod
    def get_by_owner_id(self, owner_id: UUID) -> AccountEntity | None:
        """Получить аккаунт по владельцу."""
        ...

    @abstractmethod
    def create(self, entity: AccountEntity) -> AccountEntity:
        """Создать аккаунт."""
        ...

    @abstractmethod
    def update(self, entity: AccountEntity) -> AccountEntity:
        """Обновить аккаунт."""
        ...

    @abstractmethod
    def list_all(self) -> Sequence[AccountEntity]:
        """Все аккаунты (для фоновых задач)."""
        ...

    @abstractmethod
    def list_pro_subscriptions(self) -> Sequence[AccountEntity]:
        """Аккаунты на тарифе Pro (для продления/отключения)."""
        ...


class IMembershipRepository(ABC):
    """Интерфейс репозитория memberships."""

    @abstractmethod
    def get_by_id(self, membership_id: UUID) -> MembershipEntity | None:
        """Получить membership по ID."""
        ...

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> MembershipEntity | None:
        """Получить активную membership пользователя (v1: один аккаунт)."""
        ...

    @abstractmethod
    def get_by_user_and_account(
        self, user_id: UUID, account_id: UUID
    ) -> MembershipEntity | None:
        """Получить membership по user и account."""
        ...

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Sequence[MembershipEntity]:
        """Список участников аккаунта."""
        ...

    @abstractmethod
    def create(self, entity: MembershipEntity) -> MembershipEntity:
        """Создать membership."""
        ...

    @abstractmethod
    def update(self, entity: MembershipEntity) -> MembershipEntity:
        """Обновить membership."""
        ...

    @abstractmethod
    def delete(self, membership_id: UUID) -> None:
        """Удалить membership."""
        ...

    @abstractmethod
    def count_active_by_account(self, account_id: UUID) -> int:
        """Количество активных участников аккаунта."""
        ...


class IPropertyRepository(ABC):
    """Интерфейс репозитория объектов недвижимости."""

    @abstractmethod
    def get_by_id(self, property_id: UUID, account_id: UUID) -> PropertyEntity | None:
        """Получить объект по ID в рамках аккаунта."""
        ...

    @abstractmethod
    def list_by_account(
        self,
        account_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        property_type: str | None = None,
    ) -> PaginatedResult:
        ...

    @abstractmethod
    def create(self, entity: PropertyEntity) -> PropertyEntity:
        """Создать объект."""
        ...

    @abstractmethod
    def update(self, entity: PropertyEntity) -> PropertyEntity:
        """Обновить объект."""
        ...

    @abstractmethod
    def delete(self, property_id: UUID, account_id: UUID) -> None:
        """Удалить объект."""
        ...

    @abstractmethod
    def list_by_ids(self, property_ids: Sequence[UUID], account_id: UUID) -> Sequence[PropertyEntity]:
        """Получить объекты по списку ID в рамках аккаунта."""
        ...

    @abstractmethod
    def count_active(self, account_id: UUID) -> int:
        """Количество активных объектов."""
        ...

    @abstractmethod
    def count_by_account(self, account_id: UUID) -> int:
        """Количество всех объектов аккаунта."""
        ...


class ITenantRepository(ABC):
    """Интерфейс репозитория арендаторов."""

    @abstractmethod
    def get_by_id(self, tenant_id: UUID, account_id: UUID) -> TenantEntity | None:
        """Получить арендатора по ID в рамках аккаунта."""
        ...

    @abstractmethod
    def list_by_account(
        self, account_id: UUID, page: int = 1, per_page: int = 20,
        search: str | None = None,
    ) -> PaginatedResult:
        ...

    @abstractmethod
    def list_by_ids(self, tenant_ids: Sequence[UUID], account_id: UUID) -> Sequence[TenantEntity]:
        """Получить арендаторов по списку ID в рамках аккаунта."""
        ...

    @abstractmethod
    def create(self, entity: TenantEntity) -> TenantEntity:
        """Создать арендатора."""
        ...

    @abstractmethod
    def update(self, entity: TenantEntity) -> TenantEntity:
        """Обновить арендатора."""
        ...

    @abstractmethod
    def delete(self, tenant_id: UUID, account_id: UUID) -> None:
        """Удалить арендатора."""
        ...

class IContractRepository(ABC):
    """Интерфейс репозитория контрактов."""

    @abstractmethod
    def get_by_id(self, contract_id: UUID, account_id: UUID) -> ContractEntity | None:
        """Получить контракт по ID с проверкой account_id."""
        ...

    @abstractmethod
    def get_by_id_for_update(
        self, contract_id: UUID, account_id: UUID
    ) -> ContractEntity | None:
        """Получить контракт с блокировкой строки до конца транзакции."""
        ...

    @abstractmethod
    def list_by_account(
        self, account_id: UUID, page: int = 1, per_page: int = 20,
        overdue_only: bool = False, search: str | None = None,
        status: str | None = None,
    ) -> PaginatedResult:
        """Список контрактов аккаунта с пагинацией."""
        ...

    @abstractmethod
    def list_all_by_account(
        self, account_id: UUID, overdue_only: bool = False,
    ) -> Sequence[ContractEntity]:
        """Все контракты аккаунта без пагинации."""
        ...

    @abstractmethod
    def get_active_by_property(
        self, property_id: UUID, account_id: UUID
    ) -> ContractEntity | None:
        """Получить активный контракт по объекту (active или overdue)."""
        ...

    @abstractmethod
    def create(self, entity: ContractEntity) -> ContractEntity:
        """Создать контракт."""
        ...

    @abstractmethod
    def update(self, entity: ContractEntity) -> ContractEntity:
        """Обновить контракт."""
        ...

    @abstractmethod
    def delete(self, contract_id: UUID, account_id: UUID) -> None:
        """Удалить контракт."""
        ...

    @abstractmethod
    def count_active(self, account_id: UUID) -> int:
        """Количество активных контрактов."""
        ...

    @abstractmethod
    def get_active_for_property(
        self, property_id: UUID, account_id: UUID
    ) -> ContractEntity | None:
        """Получить активный контракт для объекта."""
        ...

    @abstractmethod
    def list_active_by_properties(
        self, property_ids: Sequence[UUID], account_id: UUID
    ) -> Sequence[ContractEntity]:
        """Получить active/overdue контракты для набора объектов аккаунта."""
        ...

    @abstractmethod
    def get_active_for_tenant(
        self, tenant_id: UUID, account_id: UUID
    ) -> Sequence[ContractEntity]:
        """Получить активные контракты арендатора."""
        ...

    @abstractmethod
    def get_by_portal_token(self, portal_token: str) -> ContractEntity | None:
        """Получить контракт по публичному токену портала."""
        ...

class IRentChargeRepository(ABC):
    """Интерфейс репозитория начислений."""

    @abstractmethod
    def get_by_id(self, charge_id: UUID, account_id: UUID) -> RentChargeEntity | None:
        """Получить начисление по ID."""
        ...

    @abstractmethod
    def list_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> Sequence[RentChargeEntity]:
        """Список начислений по контракту."""
        ...

    @abstractmethod
    def list_by_contracts(
        self,
        contract_ids: Sequence[UUID],
        account_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Sequence[RentChargeEntity]:
        """Получить начисления для набора контрактов аккаунта."""
        ...

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Sequence[RentChargeEntity]:
        """Список всех начислений аккаунта."""
        ...

    @abstractmethod
    def create(self, entity: RentChargeEntity) -> RentChargeEntity:
        """Создать начисление."""
        ...

    @abstractmethod
    def create_if_absent(self, entity: RentChargeEntity) -> bool:
        """Создать начисление периода, если оно отсутствует."""
        ...

    @abstractmethod
    def update(self, entity: RentChargeEntity) -> RentChargeEntity:
        """Обновить начисление."""
        ...

    @abstractmethod
    def delete(self, charge_id: UUID, account_id: UUID) -> None:
        """Удалить начисление."""
        ...

    @abstractmethod
    def update_status(
        self, charge_id: UUID, account_id: UUID, status: str
    ) -> RentChargeEntity:
        """Обновить статус начисления."""
        ...

    @abstractmethod
    def get_total_expected_for_month(
        self, account_id: UUID, year: int, month: int
    ) -> Decimal:
        """Общая сумма начислений за месяц."""
        ...

    @abstractmethod
    def get_total_outstanding(self, account_id: UUID) -> Decimal:
        """Общая сумма непогашенных начислений."""
        ...

    @abstractmethod
    def get_overdue_total_amount(self, account_id: UUID) -> Decimal:
        """Сумма остатков по просроченным начислениям (due_date < today, remainder > 0)."""
        ...

    @abstractmethod
    def get_overdue_count(self, account_id: UUID) -> int:
        """Число просроченных начислений (due_date < today, remainder > 0)."""
        ...

    @abstractmethod
    def get_by_id_for_update(self, charge_id: UUID, account_id: UUID) -> RentChargeEntity | None:
        """Получить charge с блокировкой строки."""
        ...

    @abstractmethod
    def list_for_calendar(
        self, account_id: UUID, date_to: date
    ) -> Sequence[RentChargeEntity]:
        """Неоплаченные начисления с due_date <= date_to (просрочки + окно календаря)."""
        ...


class IPaymentRepository(ABC):
    """Интерфейс репозитория платежей."""

    @abstractmethod
    def get_by_id(self, payment_id: UUID, account_id: UUID) -> PaymentEntity | None:
        """Получить платёж по ID."""
        ...

    @abstractmethod
    def get_by_id_for_update(
        self, payment_id: UUID, account_id: UUID
    ) -> PaymentEntity | None:
        """Получить платёж с блокировкой строки."""
        ...

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Sequence[PaymentEntity]:
        """Список всех платежей аккаунта."""
        ...

    @abstractmethod
    def list_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> Sequence[PaymentEntity]:
        """Список платежей по контракту."""
        ...

    @abstractmethod
    def list_by_contracts(
        self,
        contract_ids: Sequence[UUID],
        account_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Sequence[PaymentEntity]:
        """Получить платежи для набора контрактов аккаунта."""
        ...

    @abstractmethod
    def list_by_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> Sequence[PaymentEntity]:
        """Список платежей по начислению."""
        ...

    @abstractmethod
    def has_financial_history_for_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> bool:
        """Проверить наличие текущих платежей или неизменяемых поступлений."""
        ...

    @abstractmethod
    def get_total_paid_for_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> Decimal:
        """Общая сумма платежей по начислению."""
        ...

    @abstractmethod
    def list_unlinked_for_contract_for_update(
        self, contract_id: UUID, account_id: UUID
    ) -> Sequence[PaymentEntity]:
        """Авансы (rent_charge_id IS NULL) по контракту с блокировкой строк."""
        ...

    @abstractmethod
    def get_total_unallocated_for_account(self, account_id: UUID) -> Decimal:
        """Сумма неаллоцированных платежей (авансов) по аккаунту."""
        ...

    @abstractmethod
    def create(self, entity: PaymentEntity) -> PaymentEntity:
        """Создать платёж."""
        ...

    @abstractmethod
    def create_receipt(self, entity: PaymentReceiptEntity) -> None:
        """Сохранить неизменяемый исходный факт поступления."""
        ...

    @abstractmethod
    def create_receipt_event(self, entity: PaymentReceiptEventEntity) -> None:
        """Добавить корректировку или отмену receipt."""
        ...

    @abstractmethod
    def create_allocation_event(self, entity: PaymentAllocationEventEntity) -> None:
        """Добавить allocation или компенсирующую reversal-запись."""
        ...

    @abstractmethod
    def update(self, entity: PaymentEntity) -> PaymentEntity:
        """Обновить платёж."""
        ...

    @abstractmethod
    def delete(self, payment_id: UUID, account_id: UUID) -> None:
        """Удалить платёж."""
        ...

    @abstractmethod
    def get_total_paid_for_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> Decimal:
        """Общая сумма платежей по контракту."""
        ...

    @abstractmethod
    def get_total_paid_for_month(
        self, account_id: UUID, year: int, month: int
    ) -> Decimal:
        """Общая сумма платежей за месяц."""
        ...

    @abstractmethod
    def get_monthly_income(self, account_id: UUID, year: int, month: int) -> Decimal:
        """Доход за указанный месяц."""
        ...

    @abstractmethod
    def get_by_tenant(self, tenant_id: UUID, account_id: UUID) -> Sequence[PaymentEntity]:
        """Получить все платежи арендатора."""
        ...


class IPropertyExpenseRepository(ABC):
    """Интерфейс репозитория расходов по объектам."""

    @abstractmethod
    def get_by_id(self, expense_id: UUID, account_id: UUID) -> PropertyExpenseEntity | None:
        """Получить расход по ID."""
        ...

    @abstractmethod
    def list_by_account(
        self,
        account_id: UUID,
        property_id: UUID | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Sequence[PropertyExpenseEntity]:
        """Список расходов аккаунта с фильтрацией."""
        ...

    @abstractmethod
    def list_by_property(
        self, property_id: UUID, account_id: UUID
    ) -> Sequence[PropertyExpenseEntity]:
        """Список расходов по объекту."""
        ...

    @abstractmethod
    def get_total_for_property(
        self,
        property_id: UUID,
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Decimal:
        """Сумма расходов по объекту за период."""
        ...

    @abstractmethod
    def sum_by_property_ids(
        self,
        property_ids: Sequence[UUID],
        account_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[UUID, Decimal]:
        """Сгруппировать суммы расходов по объектам аккаунта."""
        ...

    @abstractmethod
    def create(self, entity: PropertyExpenseEntity) -> PropertyExpenseEntity:
        """Создать расход."""
        ...

    @abstractmethod
    def update(self, entity: PropertyExpenseEntity) -> PropertyExpenseEntity:
        """Обновить расход."""
        ...

    @abstractmethod
    def delete(self, expense_id: UUID, account_id: UUID) -> None:
        """Удалить расход."""
        ...


class IReminderRepository(ABC):
    @abstractmethod
    def create(self, entity: ReminderEntity) -> ReminderEntity: ...

    @abstractmethod
    def get_by_charge(self, charge_id: UUID, account_id: UUID) -> list[ReminderEntity]: ...

    @abstractmethod
    def count_by_charge(self, charge_id: UUID, account_id: UUID) -> int: ...

class IDocumentRepository(ABC):
    @abstractmethod
    def create(self, entity: DocumentEntity) -> DocumentEntity: ...

    @abstractmethod
    def get_by_contract(self, contract_id: UUID, account_id: UUID) -> list[DocumentEntity]: ...

    @abstractmethod
    def get_by_property(self, property_id: UUID, account_id: UUID) -> list[DocumentEntity]: ...

    @abstractmethod
    def get_by_id(self, doc_id: UUID, account_id: UUID) -> DocumentEntity | None: ...

    @abstractmethod
    def delete(self, doc_id: UUID, account_id: UUID) -> bool: ...

    @abstractmethod
    def sum_size_bytes(self, account_id: UUID) -> int:
        """Суммарный размер документов аккаунта в байтах."""
        ...

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> list[DocumentEntity]:
        """Все документы аккаунта (метаданные)."""
        ...

class IContractEventRepository(ABC):

    @abstractmethod
    def create(self, entity: ContractEventEntity) -> ContractEventEntity: ...

    @abstractmethod
    def list_by_contract(
        self, contract_id: UUID, account_id: UUID, page: int = 1, per_page: int = 20,
    ) -> PaginatedResult: ...


class IContractTemplateRepository(ABC):
    """Интерфейс репозитория шаблонов договоров."""

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> Sequence[ContractTemplateEntity]:
        """Список шаблонов аккаунта."""
        ...

    @abstractmethod
    def get_by_id(
        self, template_id: UUID, account_id: UUID
    ) -> ContractTemplateEntity | None:
        """Получить шаблон по ID."""
        ...

    @abstractmethod
    def create(self, entity: ContractTemplateEntity) -> ContractTemplateEntity:
        """Создать шаблон."""
        ...

    @abstractmethod
    def update(self, entity: ContractTemplateEntity) -> ContractTemplateEntity:
        """Обновить шаблон."""
        ...

    @abstractmethod
    def delete(self, template_id: UUID, account_id: UUID) -> bool:
        """Удалить шаблон."""
        ...

    @abstractmethod
    def clear_defaults(
        self, account_id: UUID, property_type: str | None
    ) -> None:
        """Снять is_default у шаблонов того же типа."""
        ...


class INotificationDismissalRepository(ABC):
    """Интерфейс репозитория скрытых уведомлений."""

    @abstractmethod
    def list_keys(self, account_id: UUID, user_id: UUID) -> set[str]:
        """Получить множество скрытых ключей пользователя."""
        ...

    @abstractmethod
    def dismiss(
        self, entity: NotificationDismissalEntity
    ) -> NotificationDismissalEntity:
        """Скрыть уведомление (idempotent по ключу)."""
        ...


class IEmailDispatchLogRepository(ABC):
    """Интерфейс лога отправленных email-уведомлений."""

    @abstractmethod
    def was_sent_recently(
        self, account_id: UUID, notification_key: str, within_days: int
    ) -> bool:
        """True, если ключ уже отправляли за within_days дней."""
        ...

    @abstractmethod
    def record(self, entity: EmailDispatchLogEntity) -> EmailDispatchLogEntity:
        """Записать факт отправки (upsert по ключу)."""
        ...


class IAccountInviteRepository(ABC):
    """Интерфейс репозитория приглашений в аккаунт."""

    @abstractmethod
    def create(self, entity: AccountInviteEntity) -> AccountInviteEntity:
        """Создать приглашение."""
        ...

    @abstractmethod
    def get_by_id(self, invite_id: UUID, account_id: UUID) -> AccountInviteEntity | None:
        """Получить приглашение по id в рамках аккаунта."""
        ...

    @abstractmethod
    def get_by_token(self, token: str) -> AccountInviteEntity | None:
        """Получить приглашение по токену."""
        ...

    @abstractmethod
    def get_pending_by_email(
        self, account_id: UUID, email: str
    ) -> AccountInviteEntity | None:
        """Активное (не принятое) приглашение по email в аккаунте."""
        ...

    @abstractmethod
    def list_pending(self, account_id: UUID) -> Sequence[AccountInviteEntity]:
        """Список непринятых приглашений аккаунта."""
        ...

    @abstractmethod
    def count_pending(self, account_id: UUID) -> int:
        """Количество активных (непринятых, не истёкших) приглашений."""
        ...

    @abstractmethod
    def update(self, entity: AccountInviteEntity) -> AccountInviteEntity:
        """Обновить приглашение."""
        ...

    @abstractmethod
    def delete(self, invite_id: UUID, account_id: UUID) -> None:
        """Удалить приглашение."""
        ...


class IFeedbackRepository(ABC):
    """Интерфейс репозитория обратной связи."""

    @abstractmethod
    def create(self, entity: FeedbackEntity) -> FeedbackEntity:
        """Создать запись обратной связи."""
        ...

    @abstractmethod
    def list_by_account(self, account_id: UUID) -> list[FeedbackEntity]:
        """Список обратной связи аккаунта."""
        ...


class IInvoiceRepository(ABC):
    """Интерфейс репозитория квитанций."""

    @abstractmethod
    def create(self, entity: InvoiceEntity) -> InvoiceEntity:
        """Создать квитанцию."""
        ...

    @abstractmethod
    def update(self, entity: InvoiceEntity) -> InvoiceEntity:
        """Обновить квитанцию."""
        ...

    @abstractmethod
    def get_by_charge(self, charge_id: UUID, account_id: UUID) -> InvoiceEntity | None:
        """Получить квитанцию по начислению."""
        ...

    @abstractmethod
    def get_by_token(self, public_token: str) -> InvoiceEntity | None:
        """Получить квитанцию по активному публичному токену."""
        ...

    @abstractmethod
    def get_by_id(self, invoice_id: UUID, account_id: UUID) -> InvoiceEntity | None:
        """Получить квитанцию по ID."""
        ...


class IAuthSessionRepository(ABC):
    """Репозиторий активных JWT-сессий."""

    @abstractmethod
    def create(self, entity: AuthSessionEntity) -> AuthSessionEntity:
        """Создать сессию."""
        ...

    @abstractmethod
    def is_active(
        self, session_id: UUID, user_id: UUID, account_id: UUID, now: datetime
    ) -> bool:
        """Проверить, что сессия существует, не отозвана и не истекла."""
        ...

    @abstractmethod
    def revoke(self, session_id: UUID, revoked_at: datetime) -> None:
        """Отозвать сессию, если она ещё активна."""
        ...

    @abstractmethod
    def delete_expired(self, now: datetime) -> None:
        """Удалить истёкшие записи сессий."""
        ...

    @abstractmethod
    def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> None:
        """Отозвать все сессии пользователя после сброса пароля."""
        ...


class IPaymentClaimRepository(ABC):
    """Интерфейс репозитория заявок «я оплатил»."""

    @abstractmethod
    def create(self, entity: PaymentClaimEntity) -> PaymentClaimEntity:
        """Создать заявку."""
        ...

    @abstractmethod
    def update(self, entity: PaymentClaimEntity) -> PaymentClaimEntity:
        """Обновить заявку."""
        ...

    @abstractmethod
    def get_by_id(self, claim_id: UUID, account_id: UUID) -> PaymentClaimEntity | None:
        """Получить заявку по ID."""
        ...

    @abstractmethod
    def get_pending_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> PaymentClaimEntity | None:
        """Активная (pending) заявка по договору."""
        ...

    @abstractmethod
    def list_by_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        status: str | None = None,
    ) -> Sequence[PaymentClaimEntity]:
        """Список заявок по договору."""
        ...


class IOutboxMessageRepository(ABC):
    """Интерфейс очереди надёжной доставки фоновых команд."""

    @abstractmethod
    def create_charge_generation(self, account_id: UUID, contract_id: UUID) -> UUID:
        """Добавить команду генерации начислений в текущую транзакцию."""
        ...

    @abstractmethod
    def claim_due_batch(
        self, batch_size: int, lease_seconds: int
    ) -> list[OutboxMessageEntity]:
        """Захватить команды для dispatch с ограниченной lease."""
        ...

    @abstractmethod
    def get_for_update(
        self, outbox_id: UUID, account_id: UUID
    ) -> OutboxMessageEntity | None:
        """Получить команду с блокировкой для атомарного выполнения."""
        ...

    @abstractmethod
    def mark_published(
        self, outbox_id: UUID, account_id: UUID, lease_token: UUID
    ) -> bool:
        """Зафиксировать publish только для актуальной lease."""
        ...

    @abstractmethod
    def mark_dispatch_failure(
        self,
        outbox_id: UUID,
        account_id: UUID,
        lease_token: UUID,
        available_at: datetime,
        error_type: str,
        max_attempts: int,
    ) -> bool:
        """Назначить следующую безопасную попытку без хранения текста ошибки."""
        ...

    @abstractmethod
    def mark_completed(self, outbox_id: UUID, account_id: UUID) -> None:
        """Отметить завершение в текущей финансовой транзакции."""
        ...

    @abstractmethod
    def record_task_failure(
        self,
        outbox_id: UUID,
        account_id: UUID,
        error_type: str,
        max_failures: int,
        available_at: datetime,
    ) -> bool:
        """Зафиксировать безопасную retryable или terminal ошибку task."""
        ...

    @abstractmethod
    def backlog_snapshot(self) -> tuple[int, float, int]:
        """Вернуть pending count, возраст старейшей команды и terminal failures."""
        ...
