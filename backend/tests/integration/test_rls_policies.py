from uuid import uuid4

import pytest
from psycopg2 import connect as psycopg_connect
from app.core.config import settings
from app.scripts.provision_runtime_db_role import provision_runtime_role
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
    "payment_receipts",
    "payment_receipt_events",
    "payment_allocation_targets",
    "payment_allocation_events",
    "payment_idempotency_records",
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


def test_postgres_exporter_role_can_monitor_without_reading_application_rows(
    test_engine, tmp_path, monkeypatch
) -> None:
    password_file = tmp_path / "postgres-exporter.password"
    password_file.write_text("metrics-test-password\n", encoding="utf-8")
    monkeypatch.setattr(settings, "POSTGRES_EXPORTER_USER", "landlords_metrics", raising=False)
    monkeypatch.setattr(
        settings, "POSTGRES_EXPORTER_PASSWORD_FILE", str(password_file), raising=False
    )

    provision_runtime_role("landlords_test")

    with test_engine.connect() as connection:
        privileges = connection.execute(
            text(
                """
                SELECT role.rolcanlogin, role.rolsuper, role.rolcreaterole,
                       role.rolcreatedb, role.rolbypassrls,
                       pg_has_role('landlords_metrics', 'pg_monitor', 'MEMBER'),
                       has_database_privilege('landlords_metrics', current_database(), 'CONNECT'),
                       has_table_privilege('landlords_metrics', 'public.accounts', 'SELECT')
                FROM pg_roles AS role
                WHERE role.rolname = 'landlords_metrics'
                """
            )
        ).one_or_none()

    assert privileges == (True, False, False, False, False, True, True, False)
    with psycopg_connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname="landlords_test",
        user="landlords_metrics",
        password=password_file.read_text(encoding="utf-8").strip(),
    ) as exporter_connection:
        with exporter_connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            assert cursor.fetchone() == (1,)


def test_rls_resolver_role_is_narrow_and_owns_resolver_functions(test_engine) -> None:
    expected_columns = {
        ("account_memberships", "user_id"),
        ("account_memberships", "account_id"),
        ("account_invites", "token"),
        ("account_invites", "account_id"),
        ("invoices", "public_token"),
        ("invoices", "public_token_expires_at"),
        ("invoices", "account_id"),
        ("contracts", "portal_token"),
        ("contracts", "portal_token_expires_at"),
        ("contracts", "account_id"),
        ("accounts", "id"),
        ("task_outbox", "account_id"),
        ("task_outbox", "status"),
        ("task_outbox", "available_at"),
        ("task_outbox", "lease_until"),
    }
    with test_engine.connect() as connection:
        role = connection.execute(
            text(
                """
                SELECT rolsuper, rolbypassrls, rolcreaterole, rolcanlogin,
                       pg_has_role(current_user, 'landlords_rls_resolver', 'MEMBER')
                FROM pg_roles WHERE rolname = 'landlords_rls_resolver'
                """
            )
        ).one()
        grants = set(
            connection.execute(
                text(
                    """
                    SELECT relation.relname, attribute.attname
                    FROM pg_class AS relation
                    JOIN pg_namespace AS schema ON schema.oid = relation.relnamespace
                    JOIN pg_attribute AS attribute ON attribute.attrelid = relation.oid
                    CROSS JOIN LATERAL aclexplode(attribute.attacl) AS privilege
                    JOIN pg_roles AS grantee ON grantee.oid = privilege.grantee
                    WHERE grantee.rolname = 'landlords_rls_resolver'
                      AND schema.nspname = 'public'
                      AND privilege.privilege_type = 'SELECT'
                      AND attribute.attnum > 0
                      AND NOT attribute.attisdropped
                    """
                )
            ).all()
        )
        function_owners = set(
            connection.execute(
                text(
                    """
                    SELECT owner.rolname
                    FROM pg_proc AS function
                    JOIN pg_namespace AS schema ON schema.oid = function.pronamespace
                    JOIN pg_roles AS owner ON owner.oid = function.proowner
                    WHERE schema.nspname = 'public'
                      AND left(function.proname, 4) = 'app_'
                    """
                )
            ).scalars()
        )

    assert role == (False, True, False, False, False)
    assert grants == expected_columns
    assert function_owners == {"landlords_rls_resolver"}


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


def test_payment_trace_history_is_append_only_for_runtime_role(test_engine) -> None:
    tables = (
        "payment_receipts",
        "payment_receipt_events",
        "payment_allocation_targets",
        "payment_allocation_events",
    )
    # The bootstrap script is repeatable and must preserve append-only grants.
    provision_runtime_role("landlords_test")
    with test_engine.connect() as connection:
        privileges = connection.execute(
            text(
                "SELECT table_name, "
                "has_table_privilege(current_user, 'public.' || table_name, 'SELECT'), "
                "has_table_privilege(current_user, 'public.' || table_name, 'INSERT'), "
                "has_table_privilege(current_user, 'public.' || table_name, 'UPDATE'), "
                "has_table_privilege(current_user, 'public.' || table_name, 'DELETE') "
                "FROM unnest(:tables) AS table_name"
            ),
            {"tables": list(tables)},
        ).all()

    assert {row[0] for row in privileges} == set(tables)
    assert all(row[1:] == (True, True, False, False) for row in privileges), privileges
