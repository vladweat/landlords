"""Добавить неизменяемую историю поступлений и распределений."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.config import settings

revision: str = "05c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "04b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _legacy_snapshot() -> tuple[tuple[int, object], tuple[int, int, int]]:
    bind = op.get_bind()
    payments = bind.execute(
        sa.text("SELECT count(*), COALESCE(sum(amount), 0) FROM payments")
    ).one()
    events = bind.execute(
        sa.text(
            "SELECT count(*), "
            "count(*) FILTER (WHERE event_type = 'payment'), "
            "count(*) FILTER (WHERE event_type = 'payment' "
            "AND event_metadata ? 'payment_id') FROM contract_events"
        )
    ).one()
    return (payments[0], payments[1]), (events[0], events[1], events[2])


def _enable_tenant_rls(table_name: str) -> None:
    op.execute(sa.text(f'ALTER TABLE "{table_name}" ENABLE ROW LEVEL SECURITY'))
    op.execute(sa.text(f'ALTER TABLE "{table_name}" FORCE ROW LEVEL SECURITY'))
    op.execute(
        sa.text(
            f"CREATE POLICY tenant_isolation ON \"{table_name}\" "
            "USING (account_id = NULLIF(current_setting('app.account_id', true), '')::uuid) "
            "WITH CHECK (account_id = NULLIF(current_setting('app.account_id', true), '')::uuid)"
        )
    )


def _configure_runtime_grants() -> None:
    runtime_role = op.get_bind().dialect.identifier_preparer.quote(settings.DB_USER)
    for table_name in (
        "payment_receipts",
        "payment_receipt_events",
        "payment_allocation_targets",
        "payment_allocation_events",
    ):
        op.execute(
            f"GRANT SELECT, INSERT ON TABLE public.{table_name} TO {runtime_role}"
        )
        # Runtime role receives broad default DML grants from role provisioning;
        # financial history is append-only, so explicitly remove mutation rights.
        op.execute(
            f"REVOKE UPDATE, DELETE ON TABLE public.{table_name} FROM {runtime_role}"
        )


def _create_append_only_triggers() -> None:
    op.execute(
        """
        CREATE FUNCTION public.reject_payment_trace_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            -- Tenant deletion may cascade through the complete account-owned history.
            IF TG_OP = 'DELETE' AND pg_trigger_depth() > 1 THEN
                RETURN OLD;
            END IF;
            RAISE EXCEPTION 'Payment receipt and allocation history is append-only'
                USING ERRCODE = '55000';
        END;
        $$
        """
    )
    for table_name in (
        "payment_receipts",
        "payment_receipt_events",
        "payment_allocation_targets",
        "payment_allocation_events",
    ):
        op.execute(
            f"CREATE TRIGGER immutable_payment_trace BEFORE UPDATE OR DELETE "
            f"ON public.{table_name} FOR EACH ROW "
            "EXECUTE FUNCTION public.reject_payment_trace_mutation()"
        )


def upgrade() -> None:
    """Создать новые факты без эвристического backfill старых платежей."""
    before = _legacy_snapshot()

    # Composite keys let every new link prove account and contract ownership.
    op.create_unique_constraint(
        "uq_contracts_account_id_id", "contracts", ["account_id", "id"]
    )
    op.create_table(
        "payment_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date_paid", sa.Date(), nullable=False),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "original_amount > 0", name="ck_payment_receipts_amount_positive"
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'tenant_claim')",
            name="ck_payment_receipts_source",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id"],
            ["contracts.account_id", "contracts.id"],
            name="fk_payment_receipts_tenant_contract",
            ondelete="NO ACTION",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "contract_id",
            "id",
            name="uq_payment_receipts_tenant_contract_id",
        ),
    )
    op.create_index(
        "ix_payment_receipts_account_id", "payment_receipts", ["account_id"]
    )
    op.create_index(
        "ix_payment_receipts_contract_id", "payment_receipts", ["contract_id"]
    )

    op.create_table(
        "payment_receipt_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("amount_delta", sa.Numeric(12, 2), nullable=False),
        sa.Column("resulting_date_paid", sa.Date(), nullable=False),
        sa.Column("resulting_method", sa.String(length=20), nullable=False),
        sa.Column("resulting_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('correction', 'cancellation')",
            name="ck_payment_receipt_events_type",
        ),
        sa.CheckConstraint(
            "event_type <> 'cancellation' OR amount_delta < 0",
            name="ck_payment_receipt_events_cancellation_negative",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id"],
            [
                "payment_receipts.account_id",
                "payment_receipts.contract_id",
                "payment_receipts.id",
            ],
            name="fk_payment_receipt_events_receipt",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_receipt_events_account_id",
        "payment_receipt_events",
        ["account_id"],
    )
    op.create_index(
        "ix_payment_receipt_events_receipt_id",
        "payment_receipt_events",
        ["receipt_id"],
    )

    op.create_table(
        "payment_allocation_targets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("original_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id"],
            ["contracts.account_id", "contracts.id"],
            name="fk_payment_allocation_targets_tenant_contract",
            ondelete="NO ACTION",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "contract_id",
            "id",
            name="uq_payment_allocation_targets_tenant_contract_id",
        ),
    )
    op.create_index(
        "ix_payment_allocation_targets_account_id",
        "payment_allocation_targets",
        ["account_id"],
    )
    op.create_index(
        "ix_payment_allocation_targets_contract_id",
        "payment_allocation_targets",
        ["contract_id"],
    )
    op.create_table(
        "payment_allocation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rent_charge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reverses_event_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(event_type = 'allocation' AND amount > 0 AND reverses_event_id IS NULL) OR "
            "(event_type = 'reversal' AND amount < 0 AND reverses_event_id IS NOT NULL)",
            name="ck_payment_allocation_events_shape",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id"],
            [
                "payment_receipts.account_id",
                "payment_receipts.contract_id",
                "payment_receipts.id",
            ],
            name="fk_payment_allocation_events_receipt",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id", "rent_charge_id"],
            [
                "payment_allocation_targets.account_id",
                "payment_allocation_targets.contract_id",
                "payment_allocation_targets.id",
            ],
            name="fk_payment_allocation_events_charge_target",
            ondelete="NO ACTION",
        ),
        sa.ForeignKeyConstraint(
            ["account_id", "contract_id", "receipt_id", "reverses_event_id"],
            [
                "payment_allocation_events.account_id",
                "payment_allocation_events.contract_id",
                "payment_allocation_events.receipt_id",
                "payment_allocation_events.id",
            ],
            name="fk_payment_allocation_events_reversal_target",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "contract_id",
            "receipt_id",
            "id",
            name="uq_payment_allocation_events_receipt_id",
        ),
        sa.UniqueConstraint(
            "account_id",
            "contract_id",
            "receipt_id",
            "reverses_event_id",
            name="uq_payment_allocation_events_single_reversal",
        ),
    )
    op.create_index(
        "ix_payment_allocation_events_account_id",
        "payment_allocation_events",
        ["account_id"],
    )
    op.create_index(
        "ix_payment_allocation_events_receipt_id",
        "payment_allocation_events",
        ["receipt_id"],
    )
    op.create_index(
        "ix_payment_allocation_events_rent_charge_id",
        "payment_allocation_events",
        ["rent_charge_id"],
    )

    # Legacy rows stay intact and NULL marks their receipt/allocation provenance unknown.
    op.add_column("payments", sa.Column("receipt_id", postgresql.UUID(as_uuid=True)))
    op.add_column(
        "payments", sa.Column("allocation_event_id", postgresql.UUID(as_uuid=True))
    )
    op.create_check_constraint(
        "ck_payments_traceable_linked_allocation",
        "payments",
        "receipt_id IS NULL OR rent_charge_id IS NULL OR allocation_event_id IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_payments_allocation_requires_receipt",
        "payments",
        "receipt_id IS NOT NULL OR allocation_event_id IS NULL",
    )
    op.create_foreign_key(
        "fk_payments_receipt",
        "payments",
        "payment_receipts",
        ["account_id", "contract_id", "receipt_id"],
        ["account_id", "contract_id", "id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_payments_allocation_event",
        "payments",
        "payment_allocation_events",
        ["account_id", "contract_id", "receipt_id", "allocation_event_id"],
        ["account_id", "contract_id", "receipt_id", "id"],
        ondelete="CASCADE",
    )

    op.add_column(
        "contract_events",
        sa.Column("payment_receipt_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_contract_events_payment_receipt_id",
        "contract_events",
        ["payment_receipt_id"],
    )
    op.create_foreign_key(
        "fk_contract_events_payment_receipt",
        "contract_events",
        "payment_receipts",
        ["account_id", "contract_id", "payment_receipt_id"],
        ["account_id", "contract_id", "id"],
        ondelete="CASCADE",
    )

    for table_name in (
        "payment_receipts",
        "payment_receipt_events",
        "payment_allocation_targets",
        "payment_allocation_events",
    ):
        _enable_tenant_rls(table_name)
    _configure_runtime_grants()
    _create_append_only_triggers()

    # App writes and HTTP commits are the only source for traceable rows.
    # No safe historical grouping exists, so the migration does not infer one.
    if _legacy_snapshot() != before:
        raise RuntimeError("Payment traceability migration changed legacy payment history")


def downgrade() -> None:
    """Откат разрешён только до появления новых финансовых записей."""
    bind = op.get_bind()
    tracked_rows = bind.execute(
        sa.text(
            "SELECT (SELECT count(*) FROM payment_receipts) + "
            "(SELECT count(*) FROM payment_receipt_events) + "
            "(SELECT count(*) FROM payment_allocation_events) + "
            "(SELECT count(*) FROM payments WHERE receipt_id IS NOT NULL) + "
            "(SELECT count(*) FROM contract_events WHERE payment_receipt_id IS NOT NULL)"
        )
    ).scalar_one()
    if tracked_rows:
        raise RuntimeError(
            "Cannot downgrade payment traceability while immutable receipt history exists; "
            "export and reconcile it before removing the schema."
        )

    runtime_role = bind.dialect.identifier_preparer.quote(settings.DB_USER)
    for table_name in (
        "payment_receipts",
        "payment_receipt_events",
        "payment_allocation_targets",
        "payment_allocation_events",
    ):
        op.execute(f"REVOKE ALL ON TABLE public.{table_name} FROM {runtime_role}")
        op.execute(sa.text(f'DROP POLICY tenant_isolation ON "{table_name}"'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" NO FORCE ROW LEVEL SECURITY'))
        op.execute(sa.text(f'ALTER TABLE "{table_name}" DISABLE ROW LEVEL SECURITY'))
        op.execute(
            sa.text(f'DROP TRIGGER immutable_payment_trace ON "{table_name}"')
        )
    op.execute("DROP FUNCTION public.reject_payment_trace_mutation()")

    op.drop_constraint(
        "fk_contract_events_payment_receipt", "contract_events", type_="foreignkey"
    )
    op.drop_index("ix_contract_events_payment_receipt_id", table_name="contract_events")
    op.drop_column("contract_events", "payment_receipt_id")

    op.drop_constraint("fk_payments_allocation_event", "payments", type_="foreignkey")
    op.drop_constraint("fk_payments_receipt", "payments", type_="foreignkey")
    op.drop_constraint(
        "ck_payments_allocation_requires_receipt", "payments", type_="check"
    )
    op.drop_constraint(
        "ck_payments_traceable_linked_allocation", "payments", type_="check"
    )
    op.drop_column("payments", "allocation_event_id")
    op.drop_column("payments", "receipt_id")

    op.drop_table("payment_allocation_events")
    op.drop_table("payment_allocation_targets")
    op.drop_table("payment_receipt_events")
    op.drop_table("payment_receipts")
    op.drop_constraint("uq_contracts_account_id_id", "contracts", type_="unique")
