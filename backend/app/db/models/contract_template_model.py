"""ORM-модель шаблонов договоров."""

from uuid import UUID, uuid4

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import Base, TimestampMixin
from app.domain.entities import ContractTemplateEntity


class ContractTemplateModel(TimestampMixin, Base):
    """Таблица contract_templates."""

    __tablename__ = "contract_templates"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    property_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    def to_entity(self) -> ContractTemplateEntity:
        """Преобразовать ORM-модель в доменную сущность."""
        return ContractTemplateEntity(
            id=self.id,
            account_id=self.account_id,
            name=self.name,
            title=self.title,
            body=self.body,
            property_type=self.property_type,
            is_default=self.is_default,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_entity(cls, entity: ContractTemplateEntity) -> "ContractTemplateModel":
        """Создать ORM-модель из доменной сущности."""
        return cls(
            id=entity.id,
            account_id=entity.account_id,
            name=entity.name,
            title=entity.title,
            body=entity.body,
            property_type=entity.property_type,
            is_default=entity.is_default,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
