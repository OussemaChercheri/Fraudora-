"""sprint3_ocr_improvements_analysis

Revision ID: 006_invoice_ocr_tracking
Revises: 005_update_invoice_data
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_invoice_ocr_tracking"
down_revision: Union[str, None] = "005_update_invoice_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("error_message", sa.String(length=500), nullable=True))
    op.add_column("invoices", sa.Column("ocr_page_count", sa.Integer(), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("ocr_processing_time_ms", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("invoices", "ocr_processing_time_ms")
    op.drop_column("invoices", "ocr_page_count")
    op.drop_column("invoices", "error_message")
