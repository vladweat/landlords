"""documents_attachments_metadata

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-04 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("property_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("documents", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "category",
            sa.String(length=30),
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "mime_type",
            sa.String(length=100),
            nullable=False,
            server_default="application/pdf",
        ),
    )
    op.add_column("documents", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column(
            "source",
            sa.String(length=20),
            nullable=False,
            server_default="generated",
        ),
    )

    op.execute(
        """
        UPDATE documents
        SET category = 'contract_pdf',
            source = 'generated',
            mime_type = 'application/pdf'
        WHERE contract_id IS NOT NULL
        """
    )

    op.alter_column(
        "documents",
        "contract_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_documents_property_id_properties",
        "documents",
        "properties",
        ["property_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_documents_property_id"), "documents", ["property_id"], unique=False
    )
    op.create_check_constraint(
        "ck_documents_parent",
        "documents",
        "(contract_id IS NOT NULL AND property_id IS NULL) OR "
        "(contract_id IS NULL AND property_id IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_documents_parent", "documents", type_="check")
    op.drop_index(op.f("ix_documents_property_id"), table_name="documents")
    op.drop_constraint("fk_documents_property_id_properties", "documents", type_="foreignkey")
    op.execute("DELETE FROM documents WHERE contract_id IS NULL")
    op.alter_column(
        "documents",
        "contract_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.drop_column("documents", "source")
    op.drop_column("documents", "size_bytes")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "category")
    op.drop_column("documents", "title")
    op.drop_column("documents", "property_id")
