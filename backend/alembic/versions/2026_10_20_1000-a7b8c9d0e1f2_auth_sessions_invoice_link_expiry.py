"""add server-side auth sessions and invoice link expiry

Revision ID: a7b8c9d0e1f2
Revises: f7a8b9c0d1e2
Create Date: 2026-10-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("password_reset_token_id", sa.UUID(), nullable=True)
    )
    op.add_column(
        "contracts",
        sa.Column("portal_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Старые ссылки не имеют даты выпуска, поэтому отзываем их и требуем перевыпуск.
    op.execute(
        "UPDATE contracts "
        "SET portal_token_expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second' "
        "WHERE portal_token IS NOT NULL"
    )

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("account_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_account_id", "auth_sessions", ["account_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.add_column(
        "invoices",
        sa.Column("public_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE invoices "
        "SET public_token_expires_at = CURRENT_TIMESTAMP + INTERVAL '90 days'"
    )
    op.alter_column("invoices", "public_token_expires_at", nullable=False)
    op.create_index(
        "ix_invoices_public_token_expires_at",
        "invoices",
        ["public_token_expires_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_public_token_expires_at", table_name="invoices")
    op.drop_column("invoices", "public_token_expires_at")
    op.drop_column("contracts", "portal_token_expires_at")
    op.drop_column("users", "password_reset_token_id")
    op.drop_index("ix_auth_sessions_expires_at", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_account_id", table_name="auth_sessions")
    op.drop_index("ix_auth_sessions_user_id", table_name="auth_sessions")
    op.drop_table("auth_sessions")
