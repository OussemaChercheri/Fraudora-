"""create invoices table

Revision ID: 003_create_invoices
Revises: 002_password_reset_tokens
Create Date: 2026-06-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_create_invoices"
down_revision: Union[str, None] = "002_password_reset_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

file_type_enum = postgresql.ENUM(
    "PDF",
    "JPG",
    "PNG",
    name="file_type",
    create_type=False,
)

invoice_status_enum = postgresql.ENUM(
    "UPLOADED",
    "PROCESSING",
    "PROCESSED",
    "REVIEW_REQUIRED",
    "ERROR",
    name="invoice_status",
    create_type=False,
)


def upgrade() -> None:
    file_type_enum.create(op.get_bind(), checkfirst=True)
    invoice_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_filename", sa.String(), nullable=False),
        sa.Column("stored_filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("file_type", file_type_enum, nullable=False),
        sa.Column("file_size_kb", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            invoice_status_enum,
            nullable=False,
            server_default="UPLOADED",
        ),
        sa.Column("ocr_raw_text", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_user_id"), "invoices", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_invoices_user_id"), table_name="invoices")
    op.drop_table("invoices")
    invoice_status_enum.drop(op.get_bind(), checkfirst=True)
    file_type_enum.drop(op.get_bind(), checkfirst=True)
