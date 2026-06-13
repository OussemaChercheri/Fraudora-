"""create invoice_data table

Revision ID: 004_create_invoice_data
Revises: 003_create_invoices
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_create_invoice_data"
down_revision: Union[str, None] = "003_create_invoices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoice_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("invoice_number", sa.String(), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("supplier_name", sa.String(), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("tax_amount", sa.Float(), nullable=True),
        sa.Column("confidence_scores", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_data_invoice_id"),
        "invoice_data",
        ["invoice_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_data_invoice_id"), table_name="invoice_data")
    op.drop_table("invoice_data")
