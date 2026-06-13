import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileType(str, enum.Enum):
    PDF = "PDF"
    JPG = "JPG"
    PNG = "PNG"


class InvoiceStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ERROR = "ERROR"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    is_duplicate_confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_duplicate_alert: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    has_anomaly_alert: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, name="file_type"),
        nullable=False,
    )
    file_size_kb: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status"),
        nullable=False,
        default=InvoiceStatus.UPLOADED,
    )
    ocr_raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ocr_page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ocr_processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="invoices")
    invoice_data = relationship(
        "InvoiceData",
        back_populates="invoice",
        uselist=False,
        cascade="all, delete-orphan",
    )
