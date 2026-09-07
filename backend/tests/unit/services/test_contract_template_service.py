"""Unit-тесты сервиса шаблонов договоров."""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractTemplateEntity
from app.services.contract_template_defaults import DEFAULT_TEMPLATES
from app.services.contract_template_service import ContractTemplateService
from app.services.dto.contract_template_dto import (
    ContractTemplateCreateDTO,
    ContractTemplateUpdateDTO,
)


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def repo():
    return Mock()


@pytest.fixture
def service(repo):
    return ContractTemplateService(repo)


class TestContractTemplateService:
    def test_ensure_defaults_seeds_when_empty(self, service, repo, account_id):
        repo.list_by_account.return_value = []
        service.ensure_defaults(account_id)
        assert repo.create.call_count == len(DEFAULT_TEMPLATES)

    def test_ensure_defaults_skips_if_exists(self, service, repo, account_id):
        repo.list_by_account.return_value = [
            ContractTemplateEntity(
                id=uuid4(),
                account_id=account_id,
                name="x",
                title="T",
                body="body",
                is_default=True,
            )
        ]
        service.ensure_defaults(account_id)
        repo.create.assert_not_called()

    def test_resolve_by_property_type(self, service, repo, account_id):
        apt = ContractTemplateEntity(
            id=uuid4(),
            account_id=account_id,
            name="apt",
            title="Квартира",
            body="{{ tenant_name }}",
            property_type="apartment",
            is_default=True,
        )
        house = ContractTemplateEntity(
            id=uuid4(),
            account_id=account_id,
            name="house",
            title="Дом",
            body="house",
            property_type="house",
            is_default=True,
        )
        repo.list_by_account.return_value = [apt, house]
        resolved = service.resolve_template(account_id, "apartment")
        assert resolved.id == apt.id

    def test_resolve_explicit_id(self, service, repo, account_id):
        tid = uuid4()
        entity = ContractTemplateEntity(
            id=tid,
            account_id=account_id,
            name="custom",
            title="T",
            body="B",
        )
        repo.list_by_account.return_value = [entity]
        repo.get_by_id.return_value = entity
        resolved = service.resolve_template(account_id, "room", template_id=tid)
        assert resolved.id == tid

    def test_create_clears_defaults(self, service, repo, account_id):
        created = ContractTemplateEntity(
            id=uuid4(),
            account_id=account_id,
            name="n",
            title="t",
            body="b",
            property_type="apartment",
            is_default=True,
        )
        repo.create.return_value = created
        dto = ContractTemplateCreateDTO(
            name="n",
            title="t",
            body="b",
            property_type="apartment",
            is_default=True,
        )
        service.create_template(account_id, dto)
        repo.clear_defaults.assert_called_once_with(account_id, "apartment")

    def test_invalid_property_type(self, service, account_id):
        with pytest.raises(ValidationError):
            service.create_template(
                account_id,
                ContractTemplateCreateDTO(
                    name="n", title="t", body="b", property_type="garage"
                ),
            )

    def test_delete_missing(self, service, repo, account_id):
        repo.delete.return_value = False
        with pytest.raises(NotFoundError):
            service.delete_template(uuid4(), account_id)

    def test_update(self, service, repo, account_id):
        tid = uuid4()
        entity = ContractTemplateEntity(
            id=tid,
            account_id=account_id,
            name="old",
            title="old",
            body="old",
            property_type="apartment",
            is_default=False,
        )
        repo.get_by_id.return_value = entity
        repo.update.return_value = entity
        result = service.update_template(
            tid,
            account_id,
            ContractTemplateUpdateDTO(name="new", is_default=True),
        )
        assert result.name == "new"
        repo.clear_defaults.assert_called_once()
