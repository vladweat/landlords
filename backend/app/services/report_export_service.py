"""Сервис экспорта финансовых отчётов за период."""

import csv
import io
from datetime import date
from decimal import Decimal
from uuid import UUID

from openpyxl import Workbook

from app.core.exceptions import ValidationError
from app.domain.entities import ContractEntity
from app.domain.interfaces import (
    IContractRepository,
    IPaymentRepository,
    IPropertyExpenseRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
)
from app.domain.rules import compute_charge_status

EXPENSE_CATEGORY_LABELS = {
    "utilities": "ЖКХ",
    "repair": "Ремонт",
    "tax": "Налоги",
    "realtor_fee": "Комиссия риелтора",
    "other": "Прочее",
}

CHARGE_STATUS_LABELS = {
    "pending": "Ожидает",
    "partially_paid": "Частично",
    "paid": "Оплачено",
    "overdue": "Просрочено",
}


class ReportExportService:
    """Сборка CSV/XLSX отчётов по платежам, начислениям и расходам."""

    def __init__(
        self,
        payment_repo: IPaymentRepository,
        charge_repo: IRentChargeRepository,
        expense_repo: IPropertyExpenseRepository,
        contract_repo: IContractRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
    ) -> None:
        self.payment_repo = payment_repo
        self.charge_repo = charge_repo
        self.expense_repo = expense_repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo

    def export(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
        fmt: str = "xlsx",
        contract_ids: list[UUID] | None = None,
    ) -> tuple[bytes, str, str]:
        """Вернуть (content, media_type, filename)."""
        if end_date < start_date:
            raise ValidationError("end_date не может быть раньше start_date")
        if fmt not in ("xlsx", "csv"):
            raise ValidationError("format должен быть xlsx или csv")

        id_set = set(contract_ids) if contract_ids else None
        property_ids = (
            self._property_ids_for_contracts(account_id, id_set) if id_set else None
        )

        payments = self._payment_rows(account_id, start_date, end_date, id_set)
        charges = self._charge_rows(account_id, start_date, end_date, id_set)
        expenses = self._expense_rows(account_id, start_date, end_date, property_ids)
        summary = self._summary_rows(payments, charges, expenses, start_date, end_date)

        period = f"{start_date.isoformat()}_{end_date.isoformat()}"
        if fmt == "xlsx":
            content = self._build_xlsx(payments, charges, expenses, summary)
            return (
                content,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"report_{period}.xlsx",
            )

        content = self._build_csv(payments, charges, expenses, summary)
        return content, "text/csv; charset=utf-8", f"report_{period}.csv"

    def _property_ids_for_contracts(
        self, account_id: UUID, contract_ids: set[UUID]
    ) -> set[UUID]:
        property_ids: set[UUID] = set()
        for cid in contract_ids:
            contract = self.contract_repo.get_by_id(cid, account_id)
            if contract is not None:
                property_ids.add(contract.property_id)
        return property_ids

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

    def _payment_rows(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
        contract_ids: set[UUID] | None = None,
    ) -> list[dict[str, str]]:
        payments = self.payment_repo.list_by_account(
            account_id,
            start_date=start_date,
            end_date=end_date,
            limit=None,
        )
        contract_cache: dict[UUID, ContractEntity | None] = {}
        address_cache: dict[UUID, str] = {}
        tenant_cache: dict[UUID, str] = {}
        rows: list[dict[str, str]] = []
        for p in payments:
            if contract_ids is not None and p.contract_id not in contract_ids:
                continue
            if p.contract_id not in contract_cache:
                contract_cache[p.contract_id] = self.contract_repo.get_by_id(
                    p.contract_id, account_id
                )
            contract = contract_cache[p.contract_id]
            address, tenant_name = self._resolve_labels(
                contract, account_id, address_cache, tenant_cache
            )
            rows.append(
                {
                    "date_paid": p.date_paid.isoformat(),
                    "amount": str(p.amount),
                    "currency": p.currency,
                    "method": p.method or "",
                    "property_address": address,
                    "tenant_name": tenant_name,
                    "contract_id": str(p.contract_id),
                    "charge_id": str(p.rent_charge_id) if p.rent_charge_id else "",
                    "note": p.note or "",
                }
            )
        return rows

    def _charge_rows(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
        contract_ids: set[UUID] | None = None,
    ) -> list[dict[str, str]]:
        charges = [
            c
            for c in self.charge_repo.list_by_account(account_id)
            if start_date <= c.due_date <= end_date
            and (contract_ids is None or c.contract_id in contract_ids)
        ]
        contract_cache: dict[UUID, ContractEntity | None] = {}
        address_cache: dict[UUID, str] = {}
        tenant_cache: dict[UUID, str] = {}
        rows: list[dict[str, str]] = []
        for c in charges:
            if c.contract_id not in contract_cache:
                contract_cache[c.contract_id] = self.contract_repo.get_by_id(
                    c.contract_id, account_id
                )
            contract = contract_cache[c.contract_id]
            address, tenant_name = self._resolve_labels(
                contract, account_id, address_cache, tenant_cache
            )
            paid = self.payment_repo.get_total_paid_for_charge(c.id, account_id)
            remaining = max(c.amount - paid, Decimal("0"))
            status = compute_charge_status(c.amount, paid, c.due_date)
            rows.append(
                {
                    "period_start": c.period_start.isoformat(),
                    "period_end": c.period_end.isoformat(),
                    "due_date": c.due_date.isoformat(),
                    "amount": str(c.amount),
                    "amount_paid": str(paid),
                    "remaining": str(remaining),
                    "status": CHARGE_STATUS_LABELS.get(status, status),
                    "currency": c.currency,
                    "property_address": address,
                    "tenant_name": tenant_name,
                    "contract_id": str(c.contract_id),
                }
            )
        return rows

    def _expense_rows(
        self,
        account_id: UUID,
        start_date: date,
        end_date: date,
        property_ids: set[UUID] | None = None,
    ) -> list[dict[str, str]]:
        expenses = self.expense_repo.list_by_account(
            account_id, start_date=start_date, end_date=end_date
        )
        address_cache: dict[UUID, str] = {}
        rows: list[dict[str, str]] = []
        for e in expenses:
            if property_ids is not None and e.property_id not in property_ids:
                continue
            if e.property_id not in address_cache:
                prop = self.property_repo.get_by_id(e.property_id, account_id)
                address_cache[e.property_id] = prop.get_address() if prop else ""
            rows.append(
                {
                    "date_incurred": e.date_incurred.isoformat(),
                    "category": EXPENSE_CATEGORY_LABELS.get(e.category, e.category),
                    "amount": str(e.amount),
                    "currency": e.currency,
                    "property_address": address_cache[e.property_id],
                    "note": e.note or "",
                }
            )
        return rows

    def _summary_rows(
        self,
        payments: list[dict[str, str]],
        charges: list[dict[str, str]],
        expenses: list[dict[str, str]],
        start_date: date,
        end_date: date,
    ) -> list[dict[str, str]]:
        total_payments = sum((Decimal(r["amount"]) for r in payments), Decimal("0"))
        total_charges = sum((Decimal(r["amount"]) for r in charges), Decimal("0"))
        total_paid_on_charges = sum(
            (Decimal(r["amount_paid"]) for r in charges), Decimal("0")
        )
        outstanding = sum((Decimal(r["remaining"]) for r in charges), Decimal("0"))
        total_expenses = sum((Decimal(r["amount"]) for r in expenses), Decimal("0"))
        profit = total_payments - total_expenses
        return [
            {"metric": "Период с", "value": start_date.isoformat()},
            {"metric": "Период по", "value": end_date.isoformat()},
            {"metric": "Итого платежи", "value": str(total_payments)},
            {"metric": "Итого начисления", "value": str(total_charges)},
            {"metric": "Оплачено по начислениям", "value": str(total_paid_on_charges)},
            {"metric": "Остаток по начислениям", "value": str(outstanding)},
            {"metric": "Итого расходы", "value": str(total_expenses)},
            {"metric": "Прибыль (платежи − расходы)", "value": str(profit)},
        ]

    def _build_xlsx(
        self,
        payments: list[dict[str, str]],
        charges: list[dict[str, str]],
        expenses: list[dict[str, str]],
        summary: list[dict[str, str]],
    ) -> bytes:
        wb = Workbook()
        self._write_sheet(
            wb.active,
            "Платежи",
            [
                ("date_paid", "Дата оплаты"),
                ("amount", "Сумма"),
                ("currency", "Валюта"),
                ("method", "Способ"),
                ("property_address", "Объект"),
                ("tenant_name", "Арендатор"),
                ("contract_id", "Договор ID"),
                ("charge_id", "Начисление ID"),
                ("note", "Примечание"),
            ],
            payments,
        )
        ws_charges = wb.create_sheet("Начисления")
        self._write_sheet(
            ws_charges,
            None,
            [
                ("period_start", "Период с"),
                ("period_end", "Период по"),
                ("due_date", "Срок оплаты"),
                ("amount", "Сумма"),
                ("amount_paid", "Оплачено"),
                ("remaining", "Остаток"),
                ("status", "Статус"),
                ("currency", "Валюта"),
                ("property_address", "Объект"),
                ("tenant_name", "Арендатор"),
                ("contract_id", "Договор ID"),
            ],
            charges,
        )
        ws_expenses = wb.create_sheet("Расходы")
        self._write_sheet(
            ws_expenses,
            None,
            [
                ("date_incurred", "Дата"),
                ("category", "Категория"),
                ("amount", "Сумма"),
                ("currency", "Валюта"),
                ("property_address", "Объект"),
                ("note", "Примечание"),
            ],
            expenses,
        )
        ws_summary = wb.create_sheet("Сводка")
        self._write_sheet(
            ws_summary,
            None,
            [("metric", "Показатель"), ("value", "Значение")],
            summary,
        )
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _write_sheet(
        self,
        ws,
        title: str | None,
        columns: list[tuple[str, str]],
        rows: list[dict[str, str]],
    ) -> None:
        if title:
            ws.title = title
        headers = [label for _, label in columns]
        ws.append(headers)
        keys = [key for key, _ in columns]
        for row in rows:
            ws.append([row.get(k, "") for k in keys])

    def _build_csv(
        self,
        payments: list[dict[str, str]],
        charges: list[dict[str, str]],
        expenses: list[dict[str, str]],
        summary: list[dict[str, str]],
    ) -> bytes:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["type", "date", "amount", "currency", "category_or_status", "property_address", "tenant_name", "contract_id", "note"])
        for r in payments:
            writer.writerow(
                [
                    "payment",
                    r["date_paid"],
                    r["amount"],
                    r["currency"],
                    r["method"],
                    r["property_address"],
                    r["tenant_name"],
                    r["contract_id"],
                    r["note"],
                ]
            )
        for r in charges:
            writer.writerow(
                [
                    "charge",
                    r["due_date"],
                    r["amount"],
                    r["currency"],
                    r["status"],
                    r["property_address"],
                    r["tenant_name"],
                    r["contract_id"],
                    f"paid={r['amount_paid']}; remaining={r['remaining']}",
                ]
            )
        for r in expenses:
            writer.writerow(
                [
                    "expense",
                    r["date_incurred"],
                    r["amount"],
                    r["currency"],
                    r["category"],
                    r["property_address"],
                    "",
                    "",
                    r["note"],
                ]
            )
        writer.writerow([])
        writer.writerow(["summary", "metric", "value"])
        for r in summary:
            writer.writerow(["summary", r["metric"], r["value"]])
        # UTF-8 BOM for Excel
        return ("\ufeff" + buf.getvalue()).encode("utf-8")
