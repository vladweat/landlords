"""Реализация репозитория напоминаний."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.reminder_model import ReminderModel
from app.domain.entities import ReminderEntity
from app.domain.interfaces import IReminderRepository


class ReminderRepository(IReminderRepository):
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: ReminderEntity) -> ReminderEntity:
        model = ReminderModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def get_by_charge(self, charge_id: UUID, account_id: UUID) -> list[ReminderEntity]:
        models = (
            self.session.query(ReminderModel)
            .filter_by(charge_id=charge_id, account_id=account_id)
            .order_by(ReminderModel.created_at.desc())
            .all()
        )
        return [m.to_entity() for m in models]

    def count_by_charge(self, charge_id: UUID, account_id: UUID) -> int:
        return (
            self.session.query(ReminderModel)
            .filter_by(charge_id=charge_id, account_id=account_id)
            .count()
        )