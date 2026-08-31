"""Celery-задачи для работы с начислениями."""

from uuid import UUID
from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import DBAPIError, OperationalError

from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.session import SessionLocal
from app.services.rent_charge_service import RentChargeService

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.charge_tasks.generate_charges_for_contract",
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=120,
    time_limit=180,
    autoretry_for=(OperationalError, DBAPIError),
)
def generate_charges_for_contract(
    account_id: str,
    contract_id: str,
) -> dict:
    """Сгенерировать начисления для контракта."""
    logger.info(
        "Generating charges for contract account_id=%s contract_id=%s",
        account_id,
        contract_id,
    )

    session = SessionLocal()
    try:
        charge_repo = RentChargeRepository(session)
        payment_repo = PaymentRepository(session)
        contract_repo = ContractRepository(session)

        service = RentChargeService(charge_repo, payment_repo, contract_repo)
        charges = service.create_charges_batch(
            account_id=UUID(account_id),
            contract_id=UUID(contract_id),
        )

        session.commit()

        logger.info(
            "Charges generated successfully contract_id=%s count=%d",
            contract_id,
            len(charges),
        )

        return {
            "status": "success",
            "contract_id": contract_id,
            "charges_created": len(charges),
        }

    except Exception:
        session.rollback()
        logger.exception("Failed to generate charges contract_id=%s", contract_id)
        raise
    finally:
        session.close()


@shared_task(
    name="app.tasks.charge_tasks.update_overdue_charges",
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=300,
    time_limit=600,
)
def update_overdue_charges() -> dict:
    """Обновить статус просроченных начислений и контрактов."""
    from sqlalchemy import update as sql_update

    from app.db.models.contract_model import ContractModel
    from app.db.models.rent_charge_model import RentChargeModel
    from app.services.contract_status import check_and_update_contract_status

    logger.info("Updating overdue charges and contracts")

    session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        charge_repo = RentChargeRepository(session)
        payment_repo = PaymentRepository(session)
        contract_repo = ContractRepository(session)

        # 1. Обновляем charges: pending → overdue
        charges_result = session.execute(
            sql_update(RentChargeModel)
            .where(
                RentChargeModel.due_date < today,
                RentChargeModel.status == "pending",
            )
            .values(status="overdue")
        )
        charges_updated = charges_result.rowcount

        # 2. Находим контракты с overdue charges и переводим active → overdue
        overdue_contract_ids = (
            session.query(RentChargeModel.contract_id)
            .filter(
                RentChargeModel.status == "overdue",
                RentChargeModel.due_date < today,
            )
            .distinct()
            .subquery()
        )

        contracts_result = session.execute(
            sql_update(ContractModel)
            .where(
                ContractModel.id.in_(session.query(overdue_contract_ids)),
                ContractModel.status == "active",
            )
            .values(status="overdue")
        )
        contracts_to_overdue = contracts_result.rowcount

        # 3. Возвращаем оплаченные контракты в active
        overdue_contracts = (
            session.query(ContractModel).filter_by(status="overdue").all()
        )
        contracts_to_active = 0
        for contract in overdue_contracts:
            old_status = contract.status
            check_and_update_contract_status(
                charge_repo, payment_repo, contract_repo,
                contract.id, contract.account_id,
            )
            if old_status != contract.status:
                contracts_to_active += 1

        session.commit()

        logger.info(
            "Updated overdue charges=%d contracts_to_overdue=%d contracts_to_active=%d",
            charges_updated,
            contracts_to_overdue,
            contracts_to_active,
        )
        return {
            "status": "success",
            "charges_updated": charges_updated,
            "contracts_to_overdue": contracts_to_overdue,
            "contracts_to_active": contracts_to_active,
        }

    except Exception:
        session.rollback()
        logger.exception("Failed to update overdue charges")
        raise
    finally:
        session.close()