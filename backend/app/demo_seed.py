"""Showcase-данные для портфолио-демо (идемпотентно по маркеру в notes)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from app.core.exceptions import ConflictError
from app.db.repositories.account_repo import AccountRepository
from app.db.repositories.contract_event_repo import ContractEventRepository
from app.db.repositories.contract_repo import ContractRepository
from app.db.repositories.membership_repo import MembershipRepository
from app.db.repositories.payment_repo import PaymentRepository
from app.db.repositories.property_expense_repo import PropertyExpenseRepository
from app.db.repositories.property_repo import PropertyRepository
from app.db.repositories.reminder_repo import ReminderRepository
from app.db.repositories.rent_charge_repo import RentChargeRepository
from app.db.repositories.tenant_repo import TenantRepository
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.domain.rules import compute_charge_status
from app.services.contract_event_service import ContractEventService
from app.services.contract_service import ContractService
from app.services.dto.contract_dto import ContractCreateDTO, ContractUpdateDTO
from app.services.dto.contract_event_dto import CreateNoteDTO
from app.services.dto.payment_dto import PaymentCreateDTO
from app.services.dto.property_dto import PropertyCreateDTO
from app.services.dto.property_expense_dto import PropertyExpenseCreateDTO
from app.services.dto.reminder_dto import ReminderCreateDTO
from app.services.dto.tenant_dto import TenantCreateDTO
from app.services.dto.user_dto import UserCreateDTO
from app.services.payment_service import PaymentService
from app.services.property_expense_service import PropertyExpenseService
from app.services.property_service import PropertyService
from app.services.reminder_service import ReminderService
from app.services.rent_charge_service import RentChargeService
from app.services.tenant_service import TenantService
from app.services.user_service import UserService

DEFAULT_DEMO_EMAIL = "demo@example.com"
DEFAULT_DEMO_PASSWORD = "ChangeMeDemo1!"
DEFAULT_DEMO_FULL_NAME = "Демо Арендодатель"
SEED_MARKER = "[seed-demo-2026]"


def _sync_charge_statuses(charge_repo, payment_repo, account_id: UUID, charges) -> None:
    for ch in charges:
        total = payment_repo.get_total_paid_for_charge(ch.id, account_id)
        status = compute_charge_status(ch.amount, total, ch.due_date)
        charge_repo.update_status(ch.id, account_id, status)


def _ensure_user(
    session,
    *,
    email: str,
    password: str,
    full_name: str,
) -> tuple:
    """Найти пользователя или создать через register (минуя HTTP-флаг)."""
    user_repo = UserRepository(session)
    membership_repo = MembershipRepository(session)
    user = user_repo.get_by_email(email)
    if user:
        membership = membership_repo.get_by_user_id(user.id)
        if not membership or not membership.is_active:
            raise RuntimeError("no active membership")
        return user, membership.account_id

    user_service = UserService(
        user_repo,
        AccountRepository(session),
        membership_repo,
    )
    try:
        user_dto, account_dto, _token = user_service.register(
            UserCreateDTO(email=email, password=password, full_name=full_name)
        )
    except ConflictError:
        user = user_repo.get_by_email(email)
        if not user:
            raise
        membership = membership_repo.get_by_user_id(user.id)
        if not membership or not membership.is_active:
            raise RuntimeError("no active membership")
        return user, membership.account_id

    # register returns DTOs; reload ORM user for id consistency with services
    user = user_repo.get_by_email(email)
    if not user:
        raise RuntimeError(f"user {email} missing after register")
    return user, account_dto.id


def seed_showcase_data(
    session,
    *,
    user_id: UUID,
    account_id: UUID,
) -> bool:
    """Наполнить аккаунт showcase-данными. False — уже применено."""
    today = date.today()
    tenant_repo = TenantRepository(session)
    property_repo = PropertyRepository(session)
    contract_repo = ContractRepository(session)
    charge_repo = RentChargeRepository(session)
    payment_repo = PaymentRepository(session)
    expense_repo = PropertyExpenseRepository(session)
    reminder_repo = ReminderRepository(session)
    event_repo = ContractEventRepository(session)

    existing_tenants = tenant_repo.list_by_account(account_id, page=1, per_page=100)
    if any(SEED_MARKER in (t.notes or "") for t in existing_tenants.items):
        return False

    property_service = PropertyService(property_repo)
    tenant_service = TenantService(tenant_repo)
    contract_service = ContractService(
        contract_repo, charge_repo, payment_repo, event_repo
    )
    charge_service = RentChargeService(
        charge_repo, payment_repo, contract_repo, reminder_repo
    )
    payment_service = PaymentService(
        payment_repo, contract_repo, charge_repo, event_repo
    )
    expense_service = PropertyExpenseService(expense_repo, property_repo)
    reminder_service = ReminderService(
        reminder_repo, charge_repo, contract_repo, tenant_repo, event_repo
    )
    event_service = ContractEventService(event_repo, contract_repo)

    props = [
        property_service.create_property(
            account_id,
            PropertyCreateDTO(
                city="Москва",
                street="Арбат",
                house="15",
                apartment="42",
                type="apartment",
                size_m2=58.0,
                purchase_price=Decimal("12500000"),
            ),
        ),
        property_service.create_property(
            account_id,
            PropertyCreateDTO(
                city="Санкт-Петербург",
                street="Невский проспект",
                house="28",
                apartment="7",
                type="apartment",
                size_m2=42.5,
                purchase_price=Decimal("9800000"),
            ),
        ),
        property_service.create_property(
            account_id,
            PropertyCreateDTO(
                city="Москва",
                street="Ленина",
                house="3",
                building="2",
                apartment="11",
                type="commercial",
                size_m2=18.0,
                purchase_price=Decimal("3200000"),
            ),
        ),
        property_service.create_property(
            account_id,
            PropertyCreateDTO(
                city="Казань",
                street="Баумана",
                house="9",
                type="house",
                size_m2=120.0,
                purchase_price=Decimal("15000000"),
            ),
        ),
    ]
    print(f"properties_created={len(props)}")

    tenants = [
        tenant_service.create_tenant(
            account_id,
            TenantCreateDTO(
                full_name="Анна Смирнова",
                email="anna.smirnova@example.com",
                phone="+79031112233",
                notes=f"{SEED_MARKER} стабильный арендатор",
            ),
        ),
        tenant_service.create_tenant(
            account_id,
            TenantCreateDTO(
                full_name="Дмитрий Козлов",
                email="d.kozlov@example.com",
                phone="+79034445566",
                notes=f"{SEED_MARKER} иногда задерживает оплату",
            ),
        ),
        tenant_service.create_tenant(
            account_id,
            TenantCreateDTO(
                full_name="Елена Орлова",
                email="e.orlova@example.com",
                phone="+79037778899",
                notes=f"{SEED_MARKER} новый договор (draft)",
            ),
        ),
        tenant_service.create_tenant(
            account_id,
            TenantCreateDTO(
                full_name="Сергей Новиков",
                email="s.novikov@example.com",
                phone="+79030001122",
                notes=f"{SEED_MARKER} без активного договора",
            ),
        ),
    ]
    print(f"tenants_created={len(tenants)}")

    c_active = contract_service.create_contract(
        account_id,
        ContractCreateDTO(
            property_id=props[0].id,
            tenant_id=tenants[0].id,
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 12, 31),
            rent_amount=Decimal("75000"),
            payment_day=5,
            deposit_amount=Decimal("75000"),
            auto_generate_charges=False,
        ),
    )
    contract_service.update_contract(
        c_active.id,
        account_id,
        ContractUpdateDTO(status="active"),
        user_id=user_id,
    )
    charges_active = charge_service.create_charges_batch(account_id, c_active.id)
    past = sorted(
        [c for c in charges_active if c.due_date <= today],
        key=lambda c: c.due_date,
    )
    for ch in past[:-2]:
        payment_service.create_payment(
            account_id,
            PaymentCreateDTO(
                contract_id=c_active.id,
                rent_charge_id=ch.id,
                date_paid=ch.due_date,
                amount=ch.amount,
                method="transfer",
                note="Оплата вовремя",
            ),
        )
    if len(past) >= 2:
        ch = past[-2]
        payment_service.create_payment(
            account_id,
            PaymentCreateDTO(
                contract_id=c_active.id,
                rent_charge_id=ch.id,
                date_paid=ch.due_date + timedelta(days=2),
                amount=(ch.amount / 2).quantize(Decimal("0.01")),
                method="cash",
                note="Частичная оплата",
            ),
        )
    _sync_charge_statuses(charge_repo, payment_repo, account_id, past)

    for ch in past[-2:]:
        total = payment_repo.get_total_paid_for_charge(ch.id, account_id)
        if compute_charge_status(ch.amount, total, ch.due_date) == "overdue":
            reminder_service.create_reminder(
                account_id,
                ReminderCreateDTO(charge_id=ch.id, reminder_type="first"),
            )
            break

    event_service.create_note(
        c_active.id,
        account_id,
        user_id,
        CreateNoteDTO(
            title="Ключи переданы",
            description="Акт приёма-передачи подписан, счётчики сняты.",
        ),
    )

    c_late = contract_service.create_contract(
        account_id,
        ContractCreateDTO(
            property_id=props[1].id,
            tenant_id=tenants[1].id,
            start_date=date(today.year, 3, 1),
            end_date=date(today.year + 1, 2, 28),
            rent_amount=Decimal("55000"),
            payment_day=10,
            deposit_amount=Decimal("55000"),
            auto_generate_charges=False,
        ),
    )
    contract_service.update_contract(
        c_late.id,
        account_id,
        ContractUpdateDTO(status="active"),
        user_id=user_id,
    )
    charges_late = charge_service.create_charges_batch(account_id, c_late.id)
    past_late = sorted(
        [c for c in charges_late if c.due_date <= today],
        key=lambda c: c.due_date,
    )
    for ch in past_late[: max(1, len(past_late) // 2)]:
        payment_service.create_payment(
            account_id,
            PaymentCreateDTO(
                contract_id=c_late.id,
                rent_charge_id=ch.id,
                date_paid=ch.due_date + timedelta(days=1),
                amount=ch.amount,
                method="transfer",
            ),
        )
    _sync_charge_statuses(charge_repo, payment_repo, account_id, past_late)

    for ch in past_late:
        total = payment_repo.get_total_paid_for_charge(ch.id, account_id)
        if (
            compute_charge_status(ch.amount, total, ch.due_date) == "overdue"
            and total == 0
        ):
            reminder_service.create_reminder(
                account_id,
                ReminderCreateDTO(charge_id=ch.id, reminder_type="first"),
            )
            reminder_service.create_reminder(
                account_id,
                ReminderCreateDTO(charge_id=ch.id, reminder_type="second"),
            )
            break

    if any(
        compute_charge_status(
            c.amount,
            payment_repo.get_total_paid_for_charge(c.id, account_id),
            c.due_date,
        )
        == "overdue"
        for c in past_late
    ):
        contract_service.update_contract(
            c_late.id,
            account_id,
            ContractUpdateDTO(status="overdue"),
            user_id=user_id,
        )

    contract_service.create_contract(
        account_id,
        ContractCreateDTO(
            property_id=props[2].id,
            tenant_id=tenants[2].id,
            start_date=today + timedelta(days=14),
            end_date=today + timedelta(days=379),
            rent_amount=Decimal("28000"),
            payment_day=1,
            deposit_amount=Decimal("28000"),
            auto_generate_charges=False,
        ),
    )

    expenses = [
        PropertyExpenseCreateDTO(
            property_id=props[0].id,
            category="utilities",
            amount=Decimal("4500"),
            date_incurred=today - timedelta(days=20),
            note="Коммуналка август",
        ),
        PropertyExpenseCreateDTO(
            property_id=props[0].id,
            category="repair",
            amount=Decimal("18500"),
            date_incurred=today - timedelta(days=45),
            note="Замена смесителя и сифона",
        ),
        PropertyExpenseCreateDTO(
            property_id=props[1].id,
            category="tax",
            amount=Decimal("12000"),
            date_incurred=today - timedelta(days=60),
            note="Имущественный налог (часть)",
        ),
        PropertyExpenseCreateDTO(
            property_id=props[1].id,
            category="realtor_fee",
            amount=Decimal("55000"),
            date_incurred=date(today.year, 3, 1),
            note="Комиссия риелтора за заселение",
        ),
        PropertyExpenseCreateDTO(
            property_id=props[3].id,
            category="other",
            amount=Decimal("8000"),
            date_incurred=today - timedelta(days=10),
            note="Страховка дома",
        ),
        PropertyExpenseCreateDTO(
            property_id=props[2].id,
            category="repair",
            amount=Decimal("3200"),
            date_incurred=today - timedelta(days=5),
            note="Покраска стен перед сдачей",
        ),
    ]
    for dto in expenses:
        expense_service.create_expense(account_id, dto)
    print(f"expenses_created={len(expenses)}")

    prop_items = property_repo.list_by_account(account_id, page=1, per_page=50).items
    ivanova = next(
        (p for p in prop_items if p.street == "Иванова" and p.house == "1"),
        None,
    )
    if ivanova and not contract_repo.get_active_by_property(ivanova.id, account_id):
        end = date(today.year + 1, today.month, 1) - timedelta(days=1)
        c_house = contract_service.create_contract(
            account_id,
            ContractCreateDTO(
                property_id=ivanova.id,
                tenant_id=tenants[3].id,
                start_date=today.replace(day=1),
                end_date=end,
                rent_amount=Decimal("60000"),
                payment_day=1,
                deposit_amount=Decimal("60000"),
                auto_generate_charges=False,
            ),
        )
        contract_service.update_contract(
            c_house.id,
            account_id,
            ContractUpdateDTO(status="active"),
            user_id=user_id,
        )
        house_charges = charge_service.create_charges_batch(account_id, c_house.id)
        for ch in house_charges:
            if ch.due_date < today:
                payment_service.create_payment(
                    account_id,
                    PaymentCreateDTO(
                        contract_id=c_house.id,
                        rent_charge_id=ch.id,
                        date_paid=ch.due_date,
                        amount=ch.amount,
                        method="transfer",
                    ),
                )

    return True


def run_seed_demo(
    *,
    email: str = DEFAULT_DEMO_EMAIL,
    password: str = DEFAULT_DEMO_PASSWORD,
    full_name: str = DEFAULT_DEMO_FULL_NAME,
) -> int:
    """Создать демо-пользователя (если нет) и showcase-данные."""
    session = SessionLocal()
    try:
        user, account_id = _ensure_user(
            session, email=email, password=password, full_name=full_name
        )
        print(f"user_id={user.id}")
        print(f"account_id={account_id}")
        print(f"email={email}")

        applied = seed_showcase_data(
            session, user_id=user.id, account_id=account_id
        )
        session.commit()
        if applied:
            print("ok: demo seed committed")
        else:
            print("seed already applied — nothing to do")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"error: {exc}", flush=True)
        return 1
    finally:
        session.close()
