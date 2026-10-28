"""Celery tasks for rent charges."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy.exc import OperationalError

from app.core.config import settings
from app.tasks.lock import RedisLock
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.outbox_message_repo import OutboxMessageRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_context_repo import TenantContextRepository
from app.db.session import SessionLocal
from app.db.tenant_context import set_tenant_context
from app.services.rent_charge_service import RentChargeService

logger = get_task_logger(__name__)


@shared_task(
    name="app.tasks.charge_tasks.generate_charges_for_contract",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=120,
    time_limit=180,
    # retry only for transient DB/connection errors
    autoretry_for=(OperationalError,),
)
def generate_charges_for_contract(
    account_id: str, contract_id: str, outbox_id: str | None = None
) -> dict[str, Any]:
    """Generate charges for a contract (idempotent)."""
    logger.info(
        "Generating charges for contract account_id=%s contract_id=%s",
        account_id,
        contract_id,
    )

    message_id = UUID(outbox_id) if outbox_id is not None else None
    tenant_id = UUID(account_id)
    session = SessionLocal()
    try:
        set_tenant_context(session, tenant_id)
        outbox_repo = OutboxMessageRepository(session) if message_id else None
        if outbox_repo:
            message = outbox_repo.get_for_update(message_id, tenant_id)
            if message is None:
                raise LookupError("Outbox message does not exist")
            if message.account_id != tenant_id or message.contract_id != UUID(contract_id):
                raise ValueError("Outbox message does not match charge task scope")
            if message.task_name != "app.tasks.charge_tasks.generate_charges_for_contract":
                raise ValueError("Outbox message task is not allow-listed")
            if message.status == "completed":
                return {"status": "already_completed", "outbox_id": outbox_id}
            if message.status == "failed":
                return {"status": "terminal_failure", "outbox_id": outbox_id}

        charge_repo = RentChargeRepository(session)
        payment_repo = PaymentRepository(session)
        contract_repo = ContractRepository(session)

        service = RentChargeService(charge_repo, payment_repo, contract_repo)
        charges = service.create_charges_batch(
            account_id=tenant_id,
            contract_id=UUID(contract_id),
        )

        if outbox_repo and message_id:
            outbox_repo.mark_completed(message_id, tenant_id)
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
            "outbox_id": outbox_id,
        }

    except Exception as exc:
        session.rollback()
        if message_id:
            failure_session = SessionLocal()
            try:
                set_tenant_context(failure_session, tenant_id)
                OutboxMessageRepository(failure_session).record_task_failure(
                    message_id,
                    tenant_id,
                    type(exc).__name__,
                    settings.OUTBOX_TASK_MAX_FAILURES,
                    datetime.now(timezone.utc) + timedelta(seconds=180),
                )
                failure_session.commit()
            except Exception:
                failure_session.rollback()
                logger.error(
                    "Failed to persist outbox task failure outbox_id=%s error_type=%s",
                    outbox_id,
                    type(exc).__name__,
                )
            finally:
                failure_session.close()
            logger.error(
                "Failed to generate outbox charges outbox_id=%s error_type=%s",
                outbox_id,
                type(exc).__name__,
            )
        else:
            logger.exception("Failed to generate charges contract_id=%s", contract_id)
        raise
    finally:
        session.close()


@shared_task(
    name="app.tasks.charge_tasks.update_overdue_charges",
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=300,
    time_limit=600,
    # Retry database availability/transaction failures; do not retry business errors.
    autoretry_for=(OperationalError,),
)
def update_overdue_charges() -> dict[str, Any]:
    """Update overdue charges and contract statuses (bulk task)."""
    from sqlalchemy import update as sql_update
    from app.db.models.contract_model import ContractModel
    from app.db.models.rent_charge_model import RentChargeModel
    from app.services.contract_status import check_and_update_contract_status

    logger.info("Updating overdue charges and contracts")

    # Acquire distributed lock to avoid concurrent runs across workers.
    lock = RedisLock("update_overdue_charges", ttl=900)
    if not lock.try_acquire():
        logger.info("update_overdue_charges: could not acquire lock, another worker is running")
        return {"status": "skipped", "reason": "lock_not_acquired"}

    session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        charges_updated = contracts_to_overdue = contracts_to_active = 0
        account_ids = TenantContextRepository(session).account_ids()
        for account_id in account_ids:
            set_tenant_context(session, account_id)
            charge_repo = RentChargeRepository(session)
            payment_repo = PaymentRepository(session)
            contract_repo = ContractRepository(session)

            charges_result = session.execute(
                sql_update(RentChargeModel)
                .where(
                    RentChargeModel.account_id == account_id,
                    RentChargeModel.due_date < today,
                    RentChargeModel.status.in_(("pending", "partially_paid")),
                )
                .values(status="overdue")
            )
            charges_updated += charges_result.rowcount or 0

            overdue_contract_ids = (
                session.query(RentChargeModel.contract_id)
                .filter(
                    RentChargeModel.account_id == account_id,
                    RentChargeModel.status == "overdue",
                    RentChargeModel.due_date < today,
                )
                .distinct()
                .subquery()
            )
            contracts_result = session.execute(
                sql_update(ContractModel)
                .where(
                    ContractModel.account_id == account_id,
                    ContractModel.id.in_(session.query(overdue_contract_ids)),
                    ContractModel.status == "active",
                )
                .values(status="overdue")
            )
            contracts_to_overdue += contracts_result.rowcount or 0

            overdue_contracts = (
                session.query(ContractModel)
                .filter_by(account_id=account_id, status="overdue")
                .all()
            )
            for contract in overdue_contracts:
                old_status = contract.status
                check_and_update_contract_status(
                    charge_repo,
                    payment_repo,
                    contract_repo,
                    contract.id,
                    account_id,
                )
                if old_status != contract.status:
                    contracts_to_active += 1
            session.commit()

        from app.services.ops_heartbeat import mark_beat_ok

        mark_beat_ok()

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
        # release lock and close session
        try:
            lock.release()
        except Exception:
            pass
        session.close()

