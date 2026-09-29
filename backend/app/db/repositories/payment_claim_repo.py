"""Реализация репозитория заявок «я оплатил»."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models.payment_claim_model import PaymentClaimModel
from app.domain.entities import PaymentClaimEntity
from app.domain.interfaces import IPaymentClaimRepository


class PaymentClaimRepository(IPaymentClaimRepository):
    """Реализация репозитория payment_claims на SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, entity: PaymentClaimEntity) -> PaymentClaimEntity:
        """Создать заявку."""
        model = PaymentClaimModel.from_entity(entity)
        self.session.add(model)
        self.session.flush()
        return model.to_entity()

    def update(self, entity: PaymentClaimEntity) -> PaymentClaimEntity:
        """Обновить заявку."""
        model = (
            self.session.query(PaymentClaimModel)
            .filter_by(id=entity.id, account_id=entity.account_id)
            .first()
        )
        if not model:
            raise ValueError("Payment claim not found")
        model.charge_id = entity.charge_id
        model.amount = entity.amount
        model.note = entity.note
        model.status = entity.status
        model.resolved_at = entity.resolved_at
        model.resolved_by = entity.resolved_by
        self.session.flush()
        return model.to_entity()

    def get_by_id(self, claim_id: UUID, account_id: UUID) -> PaymentClaimEntity | None:
        """Получить заявку по ID."""
        model = (
            self.session.query(PaymentClaimModel)
            .filter_by(id=claim_id, account_id=account_id)
            .first()
        )
        return model.to_entity() if model else None

    def get_pending_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> PaymentClaimEntity | None:
        """Активная (pending) заявка по договору."""
        model = (
            self.session.query(PaymentClaimModel)
            .filter_by(contract_id=contract_id, account_id=account_id, status="pending")
            .order_by(PaymentClaimModel.created_at.desc())
            .first()
        )
        return model.to_entity() if model else None

    def list_by_contract(
        self,
        contract_id: UUID,
        account_id: UUID,
        status: str | None = None,
    ) -> list[PaymentClaimEntity]:
        """Список заявок по договору."""
        query = (
            self.session.query(PaymentClaimModel)
            .filter_by(contract_id=contract_id, account_id=account_id)
            .order_by(PaymentClaimModel.created_at.desc())
        )
        if status:
            query = query.filter_by(status=status)
        return [m.to_entity() for m in query.all()]
