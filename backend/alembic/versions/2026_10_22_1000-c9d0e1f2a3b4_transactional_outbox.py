"""Add durable outbox records for HTTP-triggered charge generation.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-22 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "task_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_name", sa.String(length=160), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("task_failures", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "available_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'leased', 'published', 'completed', 'failed')",
            name="ck_task_outbox_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_task_outbox_attempts_nonnegative"),
        sa.CheckConstraint(
            "task_failures >= 0", name="ck_task_outbox_task_failures_nonnegative"
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_task_outbox_dispatchable",
        "task_outbox",
        ["status", "available_at", "lease_until", "created_at"],
    )
    op.create_index(
        "ix_task_outbox_account_contract",
        "task_outbox",
        ["account_id", "contract_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_task_outbox_account_contract", table_name="task_outbox")
    op.drop_index("ix_task_outbox_dispatchable", table_name="task_outbox")
    op.drop_table("task_outbox")
