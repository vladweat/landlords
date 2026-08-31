"""Сервис управления объектами недвижимости."""

from uuid import UUID, uuid4

from app.core.exceptions import ConflictError, NotFoundError
from app.domain.entities import PropertyEntity
from app.domain.interfaces import IContractRepository, IPropertyRepository, ITenantRepository
from app.services.dto.property_dto import ActiveContractDTO, PropertyCreateDTO, PropertyDTO, PropertyUpdateDTO

class PropertyService:
    def __init__(
        self,
        repo: IPropertyRepository,
        contract_repo: IContractRepository | None = None,
        tenant_repo: ITenantRepository | None = None,
    ) -> None:
        self.repo = repo
        self.contract_repo = contract_repo
        self.tenant_repo = tenant_repo

    def list_properties(
        self,
        account_id: UUID,
        page: int = 1,
        per_page: int = 20,
        search: str | None = None,
        property_type: str | None = None,
    ) -> dict:
        """Получить список объектов с пагинацией и поиском."""
        return self.repo.list_by_account(
            account_id, page=page, per_page=per_page,
            search=search, property_type=property_type,
        )

    def get_property(self, property_id: UUID, account_id: UUID) -> PropertyDTO:
        entity = self.repo.get_by_id(property_id, account_id)
        if not entity:
            raise NotFoundError(f"Property with id={property_id} not found")

        dto = PropertyDTO.model_validate(entity)

        if self.contract_repo and self.tenant_repo:
            contract = self.contract_repo.get_active_for_property(property_id, account_id)
            if contract:
                tenant = self.tenant_repo.get_by_id(contract.tenant_id, account_id)
                tenant_name = tenant.full_name if tenant else "Неизвестно"
                dto.active_contract = ActiveContractDTO(
                    id=contract.id,
                    tenant_name=tenant_name,
                    status=contract.status,
                    end_date=contract.end_date,
                )

        return dto

    def create_property(self, account_id: UUID, dto: PropertyCreateDTO) -> PropertyDTO:
        entity = PropertyEntity(
            id=uuid4(), account_id=account_id,
            city=dto.city, street=dto.street, house=dto.house,
            building=dto.building, apartment=dto.apartment,
            type=dto.type, size_m2=dto.size_m2, purchase_price=dto.purchase_price,
        )
        created = self.repo.create(entity)
        return PropertyDTO.model_validate(created)

    def update_property(self, property_id: UUID, account_id: UUID, dto: PropertyUpdateDTO) -> PropertyDTO:
        entity = self.repo.get_by_id(property_id, account_id)
        if not entity:
            raise NotFoundError(f"Property with id={property_id} not found")

        if dto.city is not None:
            entity.city = dto.city
        if dto.street is not None:
            entity.street = dto.street
        if dto.house is not None:
            entity.house = dto.house
        if dto.building is not None:
            entity.building = dto.building
        if dto.apartment is not None:
            entity.apartment = dto.apartment
        if dto.type is not None:
            entity.type = dto.type
        if dto.size_m2 is not None:
            entity.size_m2 = dto.size_m2
        if dto.purchase_price is not None:
            entity.purchase_price = dto.purchase_price
        if dto.status is not None:
            entity.status = dto.status

        updated = self.repo.update(entity)
        return PropertyDTO.model_validate(updated)

    def delete_property(self, property_id: UUID, account_id: UUID) -> None:
        """Удалить объект недвижимости."""
        entity = self.repo.get_by_id(property_id, account_id)
        if not entity:
            raise NotFoundError(f"Property with id={property_id} not found")

        # Проверка активных контрактов
        if self.contract_repo:
            active = self.contract_repo.get_active_for_property(property_id, account_id)
            if active:
                raise ConflictError(
                    f"Property {property_id} has an active contract and cannot be deleted"
                )

        self.repo.delete(property_id, account_id)