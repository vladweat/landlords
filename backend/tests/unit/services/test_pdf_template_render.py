"""Unit-тесты рендера PDF по шаблону."""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.domain.entities import (
    AccountEntity,
    ContractEntity,
    ContractTemplateEntity,
    PropertyEntity,
    TenantEntity,
    UserEntity,
)
from app.services.contract_template_service import ContractTemplateService
from app.services.pdf_service import PdfService


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def pdf_service(account_id):
    contract_id = uuid4()
    property_id = uuid4()
    tenant_id = uuid4()
    owner_id = uuid4()

    contract_repo = Mock()
    property_repo = Mock()
    tenant_repo = Mock()
    account_repo = Mock()
    user_repo = Mock()
    template_repo = Mock()

    contract_repo.get_by_id.return_value = ContractEntity(
        id=contract_id,
        account_id=account_id,
        property_id=property_id,
        tenant_id=tenant_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        rent_amount=Decimal("50000"),
        deposit_amount=Decimal("50000"),
        currency="RUB",
        payment_day=5,
        status="active",
    )
    property_repo.get_by_id.return_value = PropertyEntity(
        id=property_id,
        account_id=account_id,
        city="Москва",
        street="Тверская",
        house="1",
        type="apartment",
        size_m2=45.0,
    )
    tenant_repo.get_by_id.return_value = TenantEntity(
        id=tenant_id, account_id=account_id, full_name="Иван Иванов"
    )
    account_repo.get_by_id.return_value = AccountEntity(
        id=account_id, name="Аккаунт", owner_id=owner_id
    )
    user_repo.get_by_id.return_value = UserEntity(
        id=owner_id,
        email="owner@example.com",
        password_hash="x",
        full_name="Пётр Владельцев",
    )
    template = ContractTemplateEntity(
        id=uuid4(),
        account_id=account_id,
        name="apt",
        title="ДОГОВОР {{ property_type }}",
        body="Арендодатель {{ owner_name }}, наниматель {{ tenant_name }}, "
        "адрес {{ property_address }}, плата {{ rent_amount }} {{ currency }}.",
        property_type="apartment",
        is_default=True,
    )
    template_repo.list_by_account.return_value = [template]
    template_repo.get_by_id.return_value = template
    template_service = ContractTemplateService(template_repo)

    service = PdfService(
        contract_repo,
        property_repo,
        tenant_repo,
        document_repo=None,
        template_service=template_service,
        account_repo=account_repo,
        user_repo=user_repo,
    )
    return service, contract_id, template.id


class TestPdfTemplateRender:
    def test_render_contains_placeholders(self, pdf_service, account_id):
        service, contract_id, _ = pdf_service
        pdf_bytes = service.generate_contract_pdf(contract_id, account_id)
        assert pdf_bytes[:4] == b"%PDF"
        assert len(pdf_bytes) > 200

    def test_render_with_template_id(self, pdf_service, account_id):
        service, contract_id, template_id = pdf_service
        pdf_bytes = service.generate_contract_pdf(
            contract_id, account_id, template_id=template_id
        )
        assert pdf_bytes[:4] == b"%PDF"
