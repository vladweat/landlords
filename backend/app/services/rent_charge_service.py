from uuid import UUID, uuid4

from app.core.exceptions import NotFoundError
from app.domain.entities import RentChargeEntity
from app.domain.interfaces import IContractRepository, IPaymentRepository, IRentChargeRepository, IReminderRepository
from app.domain.rules import compute_charge_status
from app.services.dto.rent_charge_dto import RentChargeCreateDTO, RentChargeDTO

class RentChargeService:
    def __init__(
        self,
        charge_repo: IRentChargeRepository,
        payment_repo: IPaymentRepository,
        contract_repo: IContractRepository,
        reminder_repo: IReminderRepository | None = None,
    ) -> None:
        self.charge_repo = charge_repo
        self.payment_repo = payment_repo
        self.contract_repo = contract_repo
        self.reminder_repo = reminder_repo

    def list_charges(self, account_id: UUID) -> list[RentChargeDTO]:
        """Получить список всех начислений аккаунта."""
        entities = self.charge_repo.list_by_account(account_id)
        return [self._enrich_charge(e, account_id) for e in entities]

    def list_charges_by_contract(
        self, contract_id: UUID, account_id: UUID
    ) -> list[RentChargeDTO]:
        """Получить список начислений по контракту."""
        # Проверяем, что контракт существует и принадлежит аккаунту
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        entities = self.charge_repo.list_by_contract(contract_id, account_id)
        return [self._enrich_charge(e, account_id) for e in entities]

    def get_charge(self, charge_id: UUID, account_id: UUID) -> RentChargeDTO:
        """Получить начисление по ID."""
        entity = self.charge_repo.get_by_id(charge_id, account_id)
        if not entity:
            raise NotFoundError(f"RentCharge with id={charge_id} not found")
        return self._enrich_charge(entity, account_id)

    def _enrich_charge(self, entity: RentChargeEntity, account_id: UUID) -> RentChargeDTO:
        from datetime import date

        total_paid = self.payment_repo.get_total_paid_for_charge(entity.id, account_id)
        computed_status = compute_charge_status(entity.amount, total_paid, entity.due_date)
        entity.status = computed_status
        dto = RentChargeDTO.model_validate(entity)

        if self.reminder_repo:
            count = self.reminder_repo.count_by_charge(entity.id, account_id)
            reminders = self.reminder_repo.get_by_charge(entity.id, account_id)
            last_date = reminders[0].created_at.isoformat() if reminders else None
            can_remind = entity.status == "overdue" and (
                count == 0 or (date.today() - reminders[0].created_at.date()).days >= 3
            )
            next_type = "first" if count == 0 else ("second" if count == 1 else "third")
            dto.reminder_status = {
                "can_remind": can_remind,
                "next_reminder_type": next_type,
                "last_reminder_date": last_date,
                "total_sent": count,
            }

        return dto
    
    def create_charge(
        self, account_id: UUID, dto: RentChargeCreateDTO
    ) -> RentChargeDTO:
        """Создать одно начисление."""
        # Проверяем контракт
        contract = self.contract_repo.get_by_id(dto.contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={dto.contract_id} not found")

        entity = RentChargeEntity(
            id=uuid4(),
            account_id=account_id,
            contract_id=dto.contract_id,
            due_date=dto.due_date,
            period_start=dto.period_start,
            period_end=dto.period_end,
            amount=dto.amount,
            currency=dto.currency,
            status="pending",
        )
        created = self.charge_repo.create(entity)
        return RentChargeDTO.model_validate(created)

    def create_charges_batch(
        self, account_id: UUID, contract_id: UUID
    ) -> list[RentChargeDTO]:
        """Сгенерировать начисления для контракта (12 месяцев вперёд).

        Используется Celery-задачей при активации контракта.
        Идемпотентен: если начисления уже есть — не создаёт дубли.
        """
        contract = self.contract_repo.get_by_id(contract_id, account_id)
        if not contract:
            raise NotFoundError(f"Contract with id={contract_id} not found")

        # Проверяем, есть ли уже начисления
        existing = self.charge_repo.list_by_contract(contract_id, account_id)
        if existing:
            return [RentChargeDTO.model_validate(e) for e in existing]

        # Генерируем расписание
        from app.domain.rules import generate_charge_schedule

        schedule = generate_charge_schedule(
            start_date=contract.start_date,
            end_date=contract.end_date,
            rent_amount=contract.rent_amount,
            payment_day=contract.payment_day,
            billing_period=contract.billing_period,
        )

        charges = []
        for item in schedule:
            dto = RentChargeCreateDTO(
                contract_id=contract_id,
                due_date=item["due_date"],
                period_start=item["period_start"],
                period_end=item["period_end"],
                amount=item["amount"],
                currency=contract.currency,
            )

            charge = self.create_charge(account_id, dto)
            charges.append(charge)

        return charges