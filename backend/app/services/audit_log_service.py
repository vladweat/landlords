"""Сервис аудит-лога."""

from uuid import UUID

from app.db.models.audit_log_model import AuditLogModel
from sqlalchemy.orm import Session

class AuditService:
    """Сервис записи аудит-лога."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def log(
        self,
        user_id: UUID,
        action: str,
        entity_type: str,
        entity_id: UUID,
        old_data: dict | None = None,
        new_data: dict | None = None,
    ) -> None:
        """Записать событие в аудит-лог."""
        log_entry = AuditLogModel(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_data=old_data,
            new_data=new_data,
        )
        self.session.add(log_entry)
        # flush, но не commit — транзакция управляется снаружи
        self.session.flush()