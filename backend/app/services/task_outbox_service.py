"""Постановка фоновых команд в transactional outbox."""

from uuid import UUID

from app.domain.interfaces import IOutboxMessageRepository


class TaskOutboxService:
    """Сервис записи бизнес-команд в транзакцию вызывающего кода."""

    def __init__(self, repository: IOutboxMessageRepository) -> None:
        self.repository = repository

    def enqueue_charge_generation(self, account_id: UUID, contract_id: UUID) -> UUID:
        """Записать команду начислений и вернуть её стабильный ID."""
        return self.repository.create_charge_generation(account_id, contract_id)
