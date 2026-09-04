"""Unit-тесты сервиса вложений."""

from decimal import Decimal
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import UploadFile

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractEntity, DocumentEntity, PropertyEntity
from app.services.document_service import DocumentService, MAX_UPLOAD_BYTES


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def contract(account_id):
    return ContractEntity(
        id=uuid4(),
        account_id=account_id,
        property_id=uuid4(),
        tenant_id=uuid4(),
        start_date=datetime.now(timezone.utc).date(),
        end_date=datetime.now(timezone.utc).date(),
        rent_amount=Decimal("50000"),
        payment_day=5,
        status="active",
    )


@pytest.fixture
def prop(account_id):
    return PropertyEntity(
        id=uuid4(),
        account_id=account_id,
        city="Москва",
        street="Тверская",
        house="1",
    )


@pytest.fixture
def repos(account_id, contract, prop, tmp_path, monkeypatch):
    monkeypatch.setattr("app.services.document_service.STORAGE_DIR", str(tmp_path))
    document_repo = Mock()
    contract_repo = Mock()
    property_repo = Mock()
    contract_repo.get_by_id.return_value = contract
    property_repo.get_by_id.return_value = prop
    document_repo.create.side_effect = lambda e: e
    document_repo.get_by_id.return_value = None
    document_repo.delete.return_value = True
    return document_repo, contract_repo, property_repo


@pytest.fixture
def service(repos):
    document_repo, contract_repo, property_repo = repos
    return DocumentService(document_repo, contract_repo, property_repo)


def _upload(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers={"content-type": content_type},
    )


class TestDocumentServiceUpload:
    @pytest.mark.asyncio
    async def test_upload_contract_ok(self, service, repos, contract, account_id):
        document_repo, *_ = repos
        file = _upload("passport.pdf", b"%PDF-1.4 test", "application/pdf")
        doc = await service.upload_for_contract(
            contract.id, account_id, file, title="Паспорт", category="passport"
        )
        assert doc.contract_id == contract.id
        assert doc.property_id is None
        assert doc.category == "passport"
        assert doc.source == "uploaded"
        assert doc.mime_type == "application/pdf"
        assert doc.size_bytes == len(b"%PDF-1.4 test")
        document_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_bad_mime(self, service, contract, account_id):
        file = _upload("x.exe", b"MZ", "application/octet-stream")
        with pytest.raises(ValidationError):
            await service.upload_for_contract(contract.id, account_id, file)

    @pytest.mark.asyncio
    async def test_reject_too_large(self, service, contract, account_id):
        file = _upload("big.pdf", b"x" * (MAX_UPLOAD_BYTES + 1), "application/pdf")
        with pytest.raises(ValidationError):
            await service.upload_for_contract(contract.id, account_id, file)

    @pytest.mark.asyncio
    async def test_reject_bad_category(self, service, contract, account_id):
        file = _upload("a.pdf", b"%PDF", "application/pdf")
        with pytest.raises(ValidationError):
            await service.upload_for_contract(
                contract.id, account_id, file, category="contract_pdf"
            )

    @pytest.mark.asyncio
    async def test_contract_not_found(self, service, repos, account_id):
        _, contract_repo, _ = repos
        contract_repo.get_by_id.return_value = None
        file = _upload("a.pdf", b"%PDF", "application/pdf")
        with pytest.raises(NotFoundError):
            await service.upload_for_contract(uuid4(), account_id, file)

    @pytest.mark.asyncio
    async def test_upload_property_ok(self, service, prop, account_id):
        file = _upload("photo.jpg", b"\xff\xd8\xff", "image/jpeg")
        doc = await service.upload_for_property(
            prop.id, account_id, file, category="photo"
        )
        assert doc.property_id == prop.id
        assert doc.contract_id is None
        assert doc.category == "photo"


class TestDocumentServiceDelete:
    def test_delete_ok(self, service, repos, account_id, tmp_path, monkeypatch):
        monkeypatch.setattr("app.services.document_service.STORAGE_DIR", str(tmp_path))
        document_repo, *_ = repos
        path = tmp_path / "f.pdf"
        path.write_bytes(b"pdf")
        doc = DocumentEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=uuid4(),
            filename="f.pdf",
            file_path=str(path),
            source="uploaded",
        )
        document_repo.get_by_id.return_value = doc
        document_repo.delete.return_value = True
        service.delete(doc.id, account_id)
        assert not path.exists()

    def test_delete_not_found(self, service, repos, account_id):
        document_repo, *_ = repos
        document_repo.get_by_id.return_value = None
        with pytest.raises(NotFoundError):
            service.delete(uuid4(), account_id)
