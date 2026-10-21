"""Persist renewal attempts and prevent duplicate rent charge periods.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-21 09:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    duplicates = bind.execute(
        sa.text(
            "SELECT account_id, contract_id, period_start, period_end, COUNT(*) AS n "
            "FROM rent_charges "
            "GROUP BY account_id, contract_id, period_start, period_end "
            "HAVING COUNT(*) > 1 LIMIT 10"
        )
    ).fetchall()
    if duplicates:
        raise RuntimeError(
            "Cannot add uq_rent_charges_contract_period: duplicate rent charge "
            "periods exist. Review and reconcile these rows before retrying: "
            f"{duplicates!r}"
        )

    op.add_column(
        "accounts", sa.Column("yookassa_renewal_period_end", sa.DateTime(timezone=True))
    )
    op.add_column(
        "accounts", sa.Column("yookassa_renewal_started_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "accounts", sa.Column("yookassa_renewal_idempotence_key", sa.String(128))
    )
    op.add_column(
        "accounts", sa.Column("yookassa_renewal_payment_id", sa.String(128))
    )
    op.add_column("accounts", sa.Column("yookassa_renewal_status", sa.String(32)))
    op.create_unique_constraint(
        "uq_rent_charges_contract_period",
        "rent_charges",
        ["account_id", "contract_id", "period_start", "period_end"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_rent_charges_contract_period", "rent_charges", type_="unique"
    )
    op.drop_column("accounts", "yookassa_renewal_status")
    op.drop_column("accounts", "yookassa_renewal_payment_id")
    op.drop_column("accounts", "yookassa_renewal_idempotence_key")
    op.drop_column("accounts", "yookassa_renewal_started_at")
    op.drop_column("accounts", "yookassa_renewal_period_end")
