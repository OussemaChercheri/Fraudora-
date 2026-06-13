"""update invoice_data schema with per-field confidence columns

Revision ID: 005_update_invoice_data
Revises: 004_create_invoice_data
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_update_invoice_data"
down_revision: Union[str, None] = "004_create_invoice_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "invoice_data",
        sa.Column("confidence_invoice_number", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column("confidence_invoice_date", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column("confidence_supplier_name", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column("confidence_total_amount", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column("confidence_tax_amount", sa.Float(), server_default="0.0", nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column("is_manually_corrected", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "invoice_data",
        sa.Column(
            "correction_history",
            postgresql.JSON(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )

    op.alter_column(
        "invoice_data",
        "total_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 3),
        existing_nullable=True,
    )
    op.alter_column(
        "invoice_data",
        "tax_amount",
        existing_type=sa.Float(),
        type_=sa.Numeric(12, 3),
        existing_nullable=True,
    )
    op.drop_column("invoice_data", "confidence_scores")


def downgrade() -> None:
    op.add_column(
        "invoice_data",
        sa.Column("confidence_scores", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.alter_column(
        "invoice_data",
        "tax_amount",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "invoice_data",
        "total_amount",
        existing_type=sa.Numeric(12, 3),
        type_=sa.Float(),
        existing_nullable=True,
    )
    op.drop_column("invoice_data", "correction_history")
    op.drop_column("invoice_data", "is_manually_corrected")
    op.drop_column("invoice_data", "confidence_tax_amount")
    op.drop_column("invoice_data", "confidence_total_amount")
    op.drop_column("invoice_data", "confidence_supplier_name")
    op.drop_column("invoice_data", "confidence_invoice_date")
    op.drop_column("invoice_data", "confidence_invoice_number")
