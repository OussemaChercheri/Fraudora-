import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class InvoiceData(Base):
    __tablename__ = "invoice_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    invoice_number: Mapped[str | None] = mapped_column(String, nullable=True)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    supplier_name: Mapped[str | None] = mapped_column(String, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    confidence_invoice_number: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_invoice_date: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_supplier_name: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_tax_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_manually_corrected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    correction_history: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    invoice = relationship("Invoice", back_populates="invoice_data")
