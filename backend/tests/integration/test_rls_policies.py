from uuid import uuid4

import pytest
from app.db.models.account_model import AccountModel
from app.db.models.property_model import PropertyModel
from app.db.models.user_model import UserModel
from app.db.tenant_context import set_tenant_context
from sqlalchemy import select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

TENANT_TABLES = {
    "accounts",
    "account_invites",
    "account_memberships",
    "auth_sessions",
    "audit_logs",
    "contract_templates",
    "email_dispatch_log",
    "feedback",
    "notification_dismissals",
    "properties",
    "tenants",
    "contracts",
    "property_expenses",
    "contract_events",
    "documents",
    "rent_charges",
    "task_outbox",
    "invoices",
    "payment_claims",
    "payments",
    "reminders",
}


def _create_account_and_property(
    session: Session,
    *,
    account_id=None,
    email: str | None = None,
) -> tuple[object, object]:
    account_id = account_id or uuid4()
    user_id = uuid4()
    session.add(
        UserModel(
            id=user_id,
            email=email or f"{user_id}@rls.test",
            password_hash="test-hash",
            full_name="RLS Test",
        )
    )
    session.flush()
    set_tenant_context(session, account_id)
    session.add(AccountModel(id=account_id, name="RLS Test", owner_id=user_id))
    property_id = uuid4()
    session.add(
        PropertyModel(
            id=property_id,
            account_id=account_id,
            city="Москва",
            street="RLS",
            house="1",
            type="apartment",
            size_m2=50,
        )
    )
    session.flush()
    return account_id, property_id


def test_runtime_role_is_not_superuser_or_table_owner(test_engine) -> None:
    with test_engine.connect() as connection:
        role = connection.execute(
            text(
                """
                SELECT r.rolsuper, r.rolbypassrls, r.rolcreaterole,
                       EXISTS (
                           SELECT 1 FROM pg_tables t
                           WHERE t.schemaname = 'public'
                             AND t.tableowner = current_user
                       )
                FROM pg_roles r
                WHERE r.rolname = current_user
                """
            )
        ).one()

    assert role == (False, False, False, False)


def test_tenant_rows_are_visible_only_in_matching_context(test_engine) -> None:
    account_a = uuid4()
    account_b = uuid4()
    with Session(test_engine) as session:
        _, property_a = _create_account_and_property(session, account_id=account_a)
        _, property_b = _create_account_and_property(session, account_id=account_b)
        session.commit()

        set_tenant_context(session, account_a)
        rows_a = session.scalars(
            select(PropertyModel).where(
                PropertyModel.id.in_([property_a, property_b])
            )
        ).all()
        assert [row.id for row in rows_a] == [property_a]

        set_tenant_context(session, account_b)
        rows_b = session.scalars(
            select(PropertyModel).where(
                PropertyModel.id.in_([property_a, property_b])
            )
        ).all()
        assert [row.id for row in rows_b] == [property_b]


def test_missing_context_hides_tenant_rows_and_rejects_insert(test_engine) -> None:
    account_id = uuid4()
    with Session(test_engine) as session:
        _create_account_and_property(session, account_id=account_id)
        session.commit()

    with Session(test_engine) as session:
        assert session.scalars(select(PropertyModel)).all() == []
        session.add(
            PropertyModel(
                id=uuid4(),
                account_id=account_id,
                city="Москва",
                street="No context",
                house="1",
                type="apartment",
                size_m2=20,
            )
        )
        with pytest.raises(DBAPIError):
            session.flush()


def test_mismatched_tenant_insert_and_update_are_rejected(test_engine) -> None:
    account_a = uuid4()
    account_b = uuid4()
    with Session(test_engine) as session:
        _, property_a = _create_account_and_property(session, account_id=account_a)
        _create_account_and_property(session, account_id=account_b)
        session.commit()

    with Session(test_engine) as session:
        set_tenant_context(session, account_a)
        session.add(
            PropertyModel(
                id=uuid4(),
                account_id=account_b,
                city="Москва",
                street="Wrong tenant",
                house="1",
                type="apartment",
                size_m2=20,
            )
        )
        with pytest.raises(DBAPIError):
            session.flush()
        session.rollback()

    with Session(test_engine) as session:
        set_tenant_context(session, account_a)
        with pytest.raises(DBAPIError):
            session.execute(
                update(PropertyModel)
                .where(PropertyModel.id == property_a)
                .values(account_id=account_b)
            )


def test_all_account_tables_force_row_level_security(test_engine) -> None:
    with test_engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = ANY(:table_names)
                """
            ),
            {"table_names": sorted(TENANT_TABLES)},
        ).all()

    actual = {row.relname for row in rows}
    assert actual == TENANT_TABLES
    assert all(row.relrowsecurity and row.relforcerowsecurity for row in rows)
