"""accounts billing / subscription fields

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-09-29 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "subscription_status",
            sa.String(length=32),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "accounts",
        sa.Column("subscription_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("yookassa_payment_method_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "accounts",
        sa.Column("yookassa_last_payment_id", sa.String(length=128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("accounts", "yookassa_last_payment_id")
    op.drop_column("accounts", "yookassa_payment_method_id")
    op.drop_column("accounts", "subscription_period_end")
    op.drop_column("accounts", "subscription_status")
