"""account_memberships

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "account_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=30), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", "user_id", name="uq_membership_account_user"),
        sa.UniqueConstraint("user_id", name="uq_membership_user"),
    )
    op.create_index(
        op.f("ix_account_memberships_account_id"),
        "account_memberships",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_account_memberships_user_id"),
        "account_memberships",
        ["user_id"],
        unique=False,
    )

    # Backfill: владелец каждого аккаунта → membership role=owner
    op.execute(
        """
        INSERT INTO account_memberships (id, account_id, user_id, role, is_active, created_at, updated_at)
        SELECT gen_random_uuid(), a.id, a.owner_id, 'owner', true, now(), now()
        FROM accounts a
        WHERE NOT EXISTS (
            SELECT 1 FROM account_memberships m WHERE m.user_id = a.owner_id
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_account_memberships_user_id"), table_name="account_memberships")
    op.drop_index(op.f("ix_account_memberships_account_id"), table_name="account_memberships")
    op.drop_table("account_memberships")
