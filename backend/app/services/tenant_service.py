"""Сервис управления арендаторами."""

from uuid import UUID, uuid4

from app.core.exceptions import NotFoundError
from app.domain.entities import TenantEntity
from app.domain.interfaces import IContractRepository, IPropertyRepository, ITenantRepository
from app.services.dto.tenant_dto import (
    TenantContractDTO,
    TenantCreateDTO,
    TenantDTO,
    TenantUpdateDTO,
)


class TenantService:
    def __init__(
        self,
        repo: ITenantRepository,
        contract_repo: IContractRepository | None = None,
        property_repo: IPropertyRepository | None = None,
    ) -> None:
        self.repo = repo
        self.contract_repo = contract_repo
        self.property_repo = property_repo

    def get_tenant(self, tenant_id: UUID, account_id: UUID) -> TenantDTO:
        """Получить арендатора по ID с активными контрактами."""
        entity = self.repo.get_by_id(tenant_id, account_id)
        if not entity:
            raise NotFoundError(f"Tenant with id={tenant_id} not found")

        dto = TenantDTO.model_validate(entity)

        if self.contract_repo and self.property_repo:
            contracts = self.contract_repo.get_active_for_tenant(tenant_id, account_id)
            for contract in contracts:
                prop = self.property_repo.get_by_id(contract.property_id, account_id)
                address = prop.get_address() if prop else "Неизвестно"
                dto.active_contracts.append(
                    TenantContractDTO(
                        id=contract.id,
                        property_address=address,
                        status=contract.status,
                        rent_amount=contract.rent_amount,
                        end_date=contract.end_date,
                    )
                )

        return dto

    def list_tenants(
        self,
        account_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
    ) -> dict:
        """Получить список арендаторов с пагинацией и поиском."""
        return self.repo.list_by_account(
            account_id, page=page, per_page=per_page, search=search,
        )

    def create_tenant(
        self, account_id: UUID, dto: TenantCreateDTO
    ) -> TenantDTO:
        """Создать арендатора."""
        entity = TenantEntity(
            id=uuid4(),
            account_id=account_id,
            full_name=dto.full_name,
            email=dto.email,
            phone=dto.phone,
            notes=dto.notes,
        )
        created = self.repo.create(entity)
        return TenantDTO.model_validate(created)

    def update_tenant(
        self, tenant_id: UUID, account_id: UUID, dto: TenantUpdateDTO
    ) -> TenantDTO:
        """Обновить арендатора."""
        entity = self.repo.get_by_id(tenant_id, account_id)
        if not entity:
            raise NotFoundError(f"Tenant with id={tenant_id} not found")

        if dto.full_name is not None:
            entity.full_name = dto.full_name
        if dto.email is not None:
            entity.email = dto.email
        if dto.phone is not None:
            entity.phone = dto.phone
        if dto.notes is not None:
            entity.notes = dto.notes
        if dto.is_active is not None:
            entity.is_active = dto.is_active

        updated = self.repo.update(entity)
        return TenantDTO.model_validate(updated)

    def delete_tenant(self, tenant_id: UUID, account_id: UUID) -> None:
        """Удалить арендатора."""
        entity = self.repo.get_by_id(tenant_id, account_id)
        if not entity:
            raise NotFoundError(f"Tenant with id={tenant_id} not found")
        self.repo.delete(tenant_id, account_id)