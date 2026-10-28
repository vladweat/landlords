"""Добавить защиту tenant-таблиц PostgreSQL RLS."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Глобальные users (identity lookup) и alembic_version намеренно не имеют RLS.
TENANT_TABLES: dict[str, str] = {
    "accounts": "id",
    "account_invites": "account_id",
    "account_memberships": "account_id",
    "auth_sessions": "account_id",
    "audit_logs": "account_id",
    "contract_templates": "account_id",
    "email_dispatch_log": "account_id",
    "feedback": "account_id",
    "notification_dismissals": "account_id",
    "properties": "account_id",
    "tenants": "account_id",
    "contracts": "account_id",
    "property_expenses": "account_id",
    "contract_events": "account_id",
    "documents": "account_id",
    "rent_charges": "account_id",
    "task_outbox": "account_id",
    "invoices": "account_id",
    "payment_claims": "account_id",
    "payments": "account_id",
    "reminders": "account_id",
}


def upgrade() -> None:
    """Добавить account scope в audit logs и включить fail-closed policies."""
    op.add_column("audit_logs", sa.Column("account_id", sa.UUID(), nullable=True))
    op.execute(
        """
        UPDATE audit_logs AS audit
        SET account_id = membership.account_id
        FROM account_memberships AS membership
        WHERE membership.user_id = audit.user_id
        """
    )
    unresolved = op.get_bind().execute(
        sa.text("SELECT count(*) FROM audit_logs WHERE account_id IS NULL")
    ).scalar_one()
    if unresolved:
        raise RuntimeError(
            f"Cannot enable tenant RLS: {unresolved} audit log rows have no account membership."
        )
    op.alter_column("audit_logs", "account_id", nullable=False)
    op.create_foreign_key(
        "fk_audit_logs_account_id_accounts",
        "audit_logs",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_audit_logs_account_id", "audit_logs", ["account_id"])

    for table_name, tenant_column in TENANT_TABLES.items():
        op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
        predicate = (
            f'"{tenant_column}" = '
            "NULLIF(current_setting('app.account_id', true), '')::uuid"
        )
        op.execute(
            sa.text(
                f'CREATE POLICY tenant_isolation ON "{table_name}" '
                f"USING ({predicate}) WITH CHECK ({predicate})"
            )
        )


def downgrade() -> None:
    """Отключить RLS, сохранив бизнес-строки."""
    for table_name in reversed(tuple(TENANT_TABLES)):
        op.execute(sa.text(f'DROP POLICY tenant_isolation ON "{table_name}"'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))

    op.drop_index("ix_audit_logs_account_id", table_name="audit_logs")
    op.drop_constraint(
        "fk_audit_logs_account_id_accounts", "audit_logs", type_="foreignkey"
    )
    op.drop_column("audit_logs", "account_id")
