"""notification_dismissals

Revision ID: a1b2c3d4e5f7
Revises: f6a7b8c9d0e1
Create Date: 2026-09-07 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_dismissals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notification_key", sa.String(length=120), nullable=False),
        sa.Column(
            "dismissed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "user_id",
            "notification_key",
            name="uq_notification_dismissals_key",
        ),
    )
    op.create_index(
        "ix_notification_dismissals_account_id",
        "notification_dismissals",
        ["account_id"],
    )
    op.create_index(
        "ix_notification_dismissals_user_id",
        "notification_dismissals",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notification_dismissals_user_id", table_name="notification_dismissals"
    )
    op.drop_index(
        "ix_notification_dismissals_account_id", table_name="notification_dismissals"
    )
    op.drop_table("notification_dismissals")
