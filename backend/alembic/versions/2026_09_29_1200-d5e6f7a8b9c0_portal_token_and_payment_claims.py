"""contracts.portal_token and payment_claims

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-09-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("portal_token", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_contracts_portal_token", "contracts", ["portal_token"], unique=True)

    op.create_table(
        "payment_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("charge_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["charge_id"], ["rent_charges.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_claims_account_id", "payment_claims", ["account_id"])
    op.create_index("ix_payment_claims_contract_id", "payment_claims", ["contract_id"])
    op.create_index(
        "ix_payment_claims_contract_status",
        "payment_claims",
        ["contract_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_claims_contract_status", table_name="payment_claims")
    op.drop_index("ix_payment_claims_contract_id", table_name="payment_claims")
    op.drop_index("ix_payment_claims_account_id", table_name="payment_claims")
    op.drop_table("payment_claims")
    op.drop_index("ix_contracts_portal_token", table_name="contracts")
    op.drop_column("contracts", "portal_token")
