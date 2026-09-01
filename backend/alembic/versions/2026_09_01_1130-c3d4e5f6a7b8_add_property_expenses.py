"""add_property_expenses

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-01 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "property_expenses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("date_incurred", sa.Date(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["property_id"], ["properties.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_property_expenses_account_id", "property_expenses", ["account_id"])
    op.create_index("ix_property_expenses_property_id", "property_expenses", ["property_id"])
    op.create_index("ix_property_expenses_date_incurred", "property_expenses", ["date_incurred"])
    op.create_index(
        "ix_property_expenses_property_date",
        "property_expenses",
        ["property_id", "date_incurred"],
    )


def downgrade() -> None:
    op.drop_index("ix_property_expenses_property_date", table_name="property_expenses")
    op.drop_index("ix_property_expenses_date_incurred", table_name="property_expenses")
    op.drop_index("ix_property_expenses_property_id", table_name="property_expenses")
    op.drop_index("ix_property_expenses_account_id", table_name="property_expenses")
    op.drop_table("property_expenses")
