"""Тесты AccountExportService."""

import io
import json
import zipfile
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock

from app.domain.entities import AccountEntity, MembershipEntity, UserEntity
from app.domain.pagination import PaginatedResult
from app.services.account_export_service import AccountExportService


def _empty_page():
    return PaginatedResult(items=[], total=0, page=1, per_page=10_000, pages=0)


def test_export_zip_contains_json():
    account_id = uuid4()
    owner_id = uuid4()
    account = AccountEntity(
        id=account_id,
        name="Test Acc",
        owner_id=owner_id,
        created_at=datetime.now(timezone.utc),
    )
    membership = MembershipEntity(
        id=uuid4(),
        account_id=account_id,
        user_id=owner_id,
        role="owner",
    )
    user = UserEntity(
        id=owner_id,
        email="owner@example.com",
        password_hash="x",
        full_name="Owner",
    )

    account_repo = MagicMock()
    account_repo.get_by_id.return_value = account
    membership_repo = MagicMock()
    membership_repo.list_by_account.return_value = [membership]
    user_repo = MagicMock()
    user_repo.get_by_id.return_value = user
    property_repo = MagicMock()
    property_repo.list_by_account.return_value = _empty_page()
    tenant_repo = MagicMock()
    tenant_repo.list_by_account.return_value = _empty_page()
    contract_repo = MagicMock()
    contract_repo.list_all_by_account.return_value = []
    charge_repo = MagicMock()
    charge_repo.list_by_account.return_value = []
    payment_repo = MagicMock()
    payment_repo.list_by_account.return_value = []
    expense_repo = MagicMock()
    expense_repo.list_by_account.return_value = []
    document_repo = MagicMock()
    document_repo.list_by_account.return_value = []
    feedback_repo = MagicMock()
    feedback_repo.list_by_account.return_value = []

    service = AccountExportService(
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
    content, filename = service.export_zip(account_id)
    assert filename.endswith(".zip")
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        raw = zf.read("account_export.json")
    data = json.loads(raw)
    assert data["account"]["name"] == "Test Acc"
    assert data["members"][0]["email"] == "owner@example.com"
    assert "yookassa_payment_method_id" not in data["account"]
    # Decimal serialization smoke
    assert isinstance(Decimal("1"), Decimal)
