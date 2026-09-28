"""Сервис шаблонов договоров."""

from uuid import UUID, uuid4

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import ContractTemplateEntity
from app.domain.interfaces import IContractTemplateRepository
from app.services.contract_template_defaults import DEFAULT_TEMPLATES, PLACEHOLDER_HINTS
from app.services.dto.contract_template_dto import (
    ContractTemplateCreateDTO,
    ContractTemplateDTO,
    ContractTemplateUpdateDTO,
)

ALLOWED_PROPERTY_TYPES = frozenset({"apartment", "house", "room", "commercial"})


class ContractTemplateService:
    """CRUD шаблонов и подбор default по типу объекта."""

    def __init__(self, template_repo: IContractTemplateRepository) -> None:
        self.template_repo = template_repo

    def list_templates(self, account_id: UUID) -> list[ContractTemplateDTO]:
        """Список шаблонов; при пустом аккаунте — seed дефолтов."""
        self.ensure_defaults(account_id)
        items = self.template_repo.list_by_account(account_id)
        return [ContractTemplateDTO.model_validate(i) for i in items]

    def get_template(self, template_id: UUID, account_id: UUID) -> ContractTemplateDTO:
        """Получить шаблон по ID."""
        entity = self.template_repo.get_by_id(template_id, account_id)
        if not entity:
            raise NotFoundError("Шаблон не найден")
        return ContractTemplateDTO.model_validate(entity)

    def create_template(
        self, account_id: UUID, dto: ContractTemplateCreateDTO
    ) -> ContractTemplateDTO:
        """Создать шаблон."""
        property_type = self._normalize_property_type(dto.property_type)
        if dto.is_default:
            self.template_repo.clear_defaults(account_id, property_type)
        entity = ContractTemplateEntity(
            id=uuid4(),
            account_id=account_id,
            name=dto.name.strip(),
            title=dto.title.strip(),
            body=dto.body,
            property_type=property_type,
            is_default=dto.is_default,
        )
        created = self.template_repo.create(entity)
        return ContractTemplateDTO.model_validate(created)

    def update_template(
        self, template_id: UUID, account_id: UUID, dto: ContractTemplateUpdateDTO
    ) -> ContractTemplateDTO:
        """Обновить шаблон."""
        entity = self.template_repo.get_by_id(template_id, account_id)
        if not entity:
            raise NotFoundError("Шаблон не найден")
        if dto.name is not None:
            entity.name = dto.name.strip()
        if dto.title is not None:
            entity.title = dto.title.strip()
        if dto.body is not None:
            entity.body = dto.body
        if dto.property_type is not None:
            # пустая строка → None (все типы)
            raw = dto.property_type.strip() if dto.property_type else None
            entity.property_type = self._normalize_property_type(raw or None)
        if dto.is_default is not None:
            entity.is_default = dto.is_default
            if entity.is_default:
                self.template_repo.clear_defaults(account_id, entity.property_type)
        updated = self.template_repo.update(entity)
        return ContractTemplateDTO.model_validate(updated)

    def delete_template(self, template_id: UUID, account_id: UUID) -> None:
        """Удалить шаблон."""
        if not self.template_repo.delete(template_id, account_id):
            raise NotFoundError("Шаблон не найден")

    def resolve_template(
        self,
        account_id: UUID,
        property_type: str | None,
        template_id: UUID | None = None,
    ) -> ContractTemplateEntity:
        """Выбрать шаблон: явный id → default по типу → любой default → первый."""
        self.ensure_defaults(account_id)
        if template_id is not None:
            entity = self.template_repo.get_by_id(template_id, account_id)
            if not entity:
                raise NotFoundError("Шаблон не найден")
            return entity

        items = self.template_repo.list_by_account(account_id)
        if property_type:
            typed_defaults = [
                t
                for t in items
                if t.is_default and t.property_type == property_type
            ]
            if typed_defaults:
                return typed_defaults[0]
            typed = [t for t in items if t.property_type == property_type]
            if typed:
                return typed[0]

        any_default = [t for t in items if t.is_default and t.property_type is None]
        if any_default:
            return any_default[0]
        defaults = [t for t in items if t.is_default]
        if defaults:
            return defaults[0]
        if items:
            return items[0]
        raise NotFoundError("Нет доступных шаблонов договора")

    def ensure_defaults(self, account_id: UUID) -> None:
        """Создать стандартные шаблоны, если у аккаунта их ещё нет."""
        existing = self.template_repo.list_by_account(account_id)
        if existing:
            return
        for spec in DEFAULT_TEMPLATES:
            self.template_repo.create(
                ContractTemplateEntity(
                    id=uuid4(),
                    account_id=account_id,
                    name=spec["name"],
                    title=spec["title"],
                    body=spec["body"],
                    property_type=spec["property_type"],
                    is_default=True,
                )
            )

    def placeholder_hints(self) -> list[str]:
        """Список доступных плейсхолдеров."""
        return list(PLACEHOLDER_HINTS)

    def _normalize_property_type(self, property_type: str | None) -> str | None:
        if property_type is None or property_type == "":
            return None
        if property_type not in ALLOWED_PROPERTY_TYPES:
            raise ValidationError(
                "property_type должен быть apartment, house, room, commercial или пустым"
            )
        return property_type
