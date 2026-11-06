"""Хранить результаты идемпотентного создания платежей."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.config import settings

revision: str = "04b5c6d7e8f9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создать tenant-scoped store с принудительной RLS и runtime grants."""
    op.create_table(
        "payment_idempotency_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation_scope", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "response_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed')",
            name="ck_payment_idempotency_status",
        ),
        sa.CheckConstraint(
            "(status = 'in_progress' AND response_snapshot IS NULL) OR "
            "(status = 'completed' AND response_snapshot IS NOT NULL)",
            name="ck_payment_idempotency_response_state",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"], ["accounts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "operation_scope",
            "key",
            name="uq_payment_idempotency_scope_key",
        ),
    )
    op.create_index(
        "ix_payment_idempotency_expiration",
        "payment_idempotency_records",
        ["account_id", "operation_scope", "expires_at"],
    )
    op.execute(
        "ALTER TABLE public.payment_idempotency_records ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.payment_idempotency_records FORCE ROW LEVEL SECURITY"
    )
    op.execute(
        """
        CREATE POLICY tenant_isolation ON public.payment_idempotency_records
        USING (account_id = NULLIF(current_setting('app.account_id', true), '')::uuid)
        WITH CHECK (account_id = NULLIF(current_setting('app.account_id', true), '')::uuid)
        """
    )

    runtime_role = op.get_bind().dialect.identifier_preparer.quote(settings.DB_USER)
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE "
        f"ON TABLE public.payment_idempotency_records TO {runtime_role}"
    )


def downgrade() -> None:
    """Удалить только metadata; платежи и события остаются без изменений."""
    runtime_role = op.get_bind().dialect.identifier_preparer.quote(settings.DB_USER)
    op.execute(
        "REVOKE SELECT, INSERT, UPDATE, DELETE "
        f"ON TABLE public.payment_idempotency_records FROM {runtime_role}"
    )
    op.drop_table("payment_idempotency_records")
