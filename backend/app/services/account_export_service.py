"""Выгрузка данных аккаунта (GDPR / право на копию)."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.interfaces import (
    IAccountRepository,
    IContractRepository,
    IDocumentRepository,
    IFeedbackRepository,
    IMembershipRepository,
    IPaymentRepository,
    IPropertyExpenseRepository,
    IPropertyRepository,
    IRentChargeRepository,
    ITenantRepository,
    IUserRepository,
)


def _json_default(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _serialize(items: list[Any]) -> list[dict[str, Any]]:
    return json.loads(json.dumps(items, default=_json_default))


class AccountExportService:
    """Сборка ZIP с JSON-данными аккаунта (без бинарников документов)."""

    def __init__(
        self,
        account_repo: IAccountRepository,
        membership_repo: IMembershipRepository,
        user_repo: IUserRepository,
        property_repo: IPropertyRepository,
        tenant_repo: ITenantRepository,
        contract_repo: IContractRepository,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        expense_repo: IPropertyExpenseRepository,
        document_repo: IDocumentRepository,
        feedback_repo: IFeedbackRepository,
    ) -> None:
        self.account_repo = account_repo
        self.membership_repo = membership_repo
        self.user_repo = user_repo
        self.property_repo = property_repo
        self.tenant_repo = tenant_repo
        self.contract_repo = contract_repo
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.expense_repo = expense_repo
        self.document_repo = document_repo
        self.feedback_repo = feedback_repo

    def export_zip(self, account_id: UUID) -> tuple[bytes, str]:
        """Вернуть (zip_bytes, filename)."""
        account = self.account_repo.get_by_id(account_id)
        if not account:
            raise NotFoundError("Аккаунт не найден")

        memberships = self.membership_repo.list_by_account(account_id)
        members_out: list[dict[str, Any]] = []
        for m in memberships:
            user = self.user_repo.get_by_id(m.user_id)
            members_out.append(
                {
                    "membership_id": str(m.id),
                    "user_id": str(m.user_id),
                    "role": m.role,
                    "is_active": m.is_active,
                    "email": user.email if user else None,
                    "full_name": user.full_name if user else None,
                    "phone": user.phone if user else None,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
            )

        # list_by_account для property/tenant возвращает ORM-модели через paginate
        properties = [
            m.to_entity() if hasattr(m, "to_entity") else m
            for m in self.property_repo.list_by_account(
                account_id, page=1, per_page=10_000
            ).items
        ]
        tenants = [
            m.to_entity() if hasattr(m, "to_entity") else m
            for m in self.tenant_repo.list_by_account(
                account_id, page=1, per_page=10_000
            ).items
        ]
        contracts = self.contract_repo.list_all_by_account(account_id)
        charges = self.charge_repo.list_by_account(account_id)
        payments = self.payment_repo.list_by_account(account_id, limit=None)
        expenses = self.expense_repo.list_by_account(account_id)
        documents = self.document_repo.list_by_account(account_id)
        feedback = self.feedback_repo.list_by_account(account_id)

        # Без секретов биллинга и хешей паролей
        account_out = {
            "id": str(account.id),
            "name": account.name,
            "base_currency": account.base_currency,
            "timezone": account.timezone,
            "payment_details": account.payment_details,
            "plan": account.plan,
            "subscription_status": account.subscription_status,
            "subscription_period_end": (
                account.subscription_period_end.isoformat()
                if account.subscription_period_end
                else None
            ),
            "created_at": account.created_at.isoformat() if account.created_at else None,
        }

        docs_meta = [
            {
                "id": str(d.id),
                "filename": d.filename,
                "title": d.title,
                "category": d.category,
                "mime_type": d.mime_type,
                "size_bytes": d.size_bytes,
                "source": d.source,
                "contract_id": str(d.contract_id) if d.contract_id else None,
                "property_id": str(d.property_id) if d.property_id else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ]

        payload = {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "account": account_out,
            "members": members_out,
            "properties": _serialize(properties),
            "tenants": _serialize(tenants),
            "contracts": _serialize(contracts),
            "charges": _serialize(charges),
            "payments": _serialize(payments),
            "expenses": _serialize(expenses),
            "documents": docs_meta,
            "feedback": _serialize(feedback),
        }

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "account_export.json",
                json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default),
            )
        filename = f"landlords_export_{account_id}.zip"
        return buf.getvalue(), filename
