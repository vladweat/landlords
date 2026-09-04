"""Сервис календаря платежей: просрочки, ближайшие due dates, окончания договоров."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from app.domain.entities import ContractEntity
from app.domain.interfaces import (
    IContractRepository,
    IPaymentRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import compute_charge_status
from app.services.dto.calendar_dto import CalendarEventDTO


class CalendarService:
    """Агрегация событий календаря по аккаунту."""

    def __init__(
        self,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
    ) -> None:
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo

    def get_events(
        self,
        account_id: UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[CalendarEventDTO]:
        """Собрать события календаря за окно [date_from, date_to] + все просрочки."""
        today = datetime.now(timezone.utc).date()
        if date_from is None:
            date_from = today
        if date_to is None:
            date_to = today + timedelta(days=45)

        contract_cache: dict[UUID, ContractEntity | None] = {}
        address_cache: dict[UUID, str] = {}
        tenant_cache: dict[UUID, str] = {}

        items: list[CalendarEventDTO] = []

        charges = self.charge_repo.list_for_calendar(account_id, date_to)
        for charge in charges:
            amount_paid = self.payment_repo.get_total_paid_for_charge(charge.id, account_id)
            status = compute_charge_status(charge.amount, amount_paid, charge.due_date)
            remaining = charge.amount - amount_paid
            if remaining <= 0 or status == "paid":
                continue
            # Просрочки всегда; остальные — только в окне [from, to]
            if status != "overdue" and not (date_from <= charge.due_date <= date_to):
                continue

            contract = self._get_contract(charge.contract_id, account_id, contract_cache)
            address, tenant_name = self._resolve_labels(
                contract, account_id, address_cache, tenant_cache
            )
            items.append(
                CalendarEventDTO(
                    type="charge_due",
                    date=charge.due_date,
                    contract_id=charge.contract_id,
                    property_address=address,
                    tenant_name=tenant_name,
                    charge_id=charge.id,
                    amount=charge.amount,
                    amount_paid=amount_paid,
                    remaining=remaining,
                    status=status,
                    currency=charge.currency,
                )
            )

        contracts = self.contract_repo.list_all_by_account(account_id)
        for contract in contracts:
            if contract.status not in ("active", "overdue"):
                continue
            if not contract.end_date or not (date_from <= contract.end_date <= date_to):
                continue
            address, tenant_name = self._resolve_labels(
                contract, account_id, address_cache, tenant_cache
            )
            items.append(
                CalendarEventDTO(
                    type="contract_ending",
                    date=contract.end_date,
                    contract_id=contract.id,
                    property_address=address,
                    tenant_name=tenant_name,
                    rent_amount=contract.rent_amount,
                    days_until_end=(contract.end_date - today).days,
                    currency=contract.currency,
                )
            )

        items.sort(
            key=lambda e: (
                0 if (e.type == "charge_due" and e.status == "overdue") else 1,
                e.date,
                0 if e.type == "charge_due" else 1,
            )
        )
        return items

    def _get_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        cache: dict[UUID, ContractEntity | None],
    ) -> ContractEntity | None:
        if contract_id not in cache:
            cache[contract_id] = self.contract_repo.get_by_id(contract_id, account_id)
        return cache[contract_id]

    def _resolve_labels(
        self,
        contract: ContractEntity | None,
        account_id: UUID,
        address_cache: dict[UUID, str],
        tenant_cache: dict[UUID, str],
    ) -> tuple[str, str]:
        if not contract:
            return "", ""
        if contract.property_id not in address_cache:
            prop = self.property_repo.get_by_id(contract.property_id, account_id)
            address_cache[contract.property_id] = prop.get_address() if prop else ""
        if contract.tenant_id not in tenant_cache:
            tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
            tenant_cache[contract.tenant_id] = tenant.full_name if tenant else ""
        return address_cache[contract.property_id], tenant_cache[contract.tenant_id]
