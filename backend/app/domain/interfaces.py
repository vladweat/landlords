"""Абстрактные интерфейсы репозиториев."""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Sequence
from uuid import UUID
from datetime import date

from app.domain.entities import (
    AccountEntity, ContractEntity, ContractEventEntity, DocumentEntity,
    FeedbackEntity, PaymentEntity, PropertyEntity, PropertyExpenseEntity,
    ReminderEntity, RentChargeEntity, TenantEntity, UserEntity,
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
    def get_by_owner_id(self, owner_id: UUID) -> AccountEntity | None:
        """Получить аккаунт по владельцу."""
        ...

    @abstractmethod
    def create(self, entity: AccountEntity) -> AccountEntity:
        """Создать аккаунт."""
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
    def count_active(self, account_id: UUID) -> int:
        """Количество активных объектов."""
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
    def get_active_for_tenant(
        self, tenant_id: UUID, account_id: UUID
    ) -> Sequence[ContractEntity]:
        """Получить активные контракты арендатора."""
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
    def list_by_account(self, account_id: UUID) -> Sequence[RentChargeEntity]:
        """Список всех начислений аккаунта."""
        ...

    @abstractmethod
    def create(self, entity: RentChargeEntity) -> RentChargeEntity:
        """Создать начисление."""
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
        """Общая сумма просроченных начислений."""
        ...
        
    @abstractmethod
    def get_by_id_for_update(self, charge_id: UUID, account_id: UUID) -> RentChargeEntity | None:
        """Получить charge с блокировкой строки."""
        ...


class IPaymentRepository(ABC):
    """Интерфейс репозитория платежей."""

    @abstractmethod
    def get_by_id(self, payment_id: UUID, account_id: UUID) -> PaymentEntity | None:
        """Получить платёж по ID."""
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
    def list_by_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> Sequence[PaymentEntity]:
        """Список платежей по начислению."""
        ...

    @abstractmethod
    def get_total_paid_for_charge(
        self, charge_id: UUID, account_id: UUID
    ) -> Decimal:
        """Общая сумма платежей по начислению."""
        ...

    @abstractmethod
    def create(self, entity: PaymentEntity) -> PaymentEntity:
        """Создать платёж."""
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
    def get_by_id(self, doc_id: UUID, account_id: UUID) -> DocumentEntity | None: ...
    
class IContractEventRepository(ABC):

    @abstractmethod
    def create(self, entity: ContractEventEntity) -> ContractEventEntity: ...

    @abstractmethod
    def list_by_contract(
        self, contract_id: UUID, account_id: UUID, page: int = 1, per_page: int = 20,
    ) -> PaginatedResult: ...


class IFeedbackRepository(ABC):
    """Интерфейс репозитория обратной связи."""

    @abstractmethod
    def create(self, entity: FeedbackEntity) -> FeedbackEntity:
        """Создать запись обратной связи."""
        ...