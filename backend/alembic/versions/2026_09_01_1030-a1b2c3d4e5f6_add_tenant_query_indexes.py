"""add_tenant_query_indexes

Revision ID: a1b2c3d4e5f6
Revises: 80e8a4863af0
Create Date: 2026-09-01 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "80e8a4863af0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавить индексы для tenant-scoped запросов по статусу."""
    op.create_index("ix_feedback_account_id", "feedback", ["account_id"], unique=False)
    op.create_index(
        "ix_contracts_account_status",
        "contracts",
        ["account_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_rent_charges_account_status",
        "rent_charges",
        ["account_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Откатить индексы."""
    op.drop_index("ix_rent_charges_account_status", table_name="rent_charges")
    op.drop_index("ix_contracts_account_status", table_name="contracts")
    op.drop_index("ix_feedback_account_id", table_name="feedback")
