import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class MatchType(str, enum.Enum):
    EXACT_NUMBER = "EXACT_NUMBER"
    FUZZY_SIMILARITY = "FUZZY_SIMILARITY"


class DuplicateStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
    REJECTED = "REJECTED"


class DuplicateMatch(Base):
    __tablename__ = "duplicate_matches"

    __table_args__ = (
        UniqueConstraint("invoice_id", "matched_invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matched_invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_type: Mapped[MatchType] = mapped_column(
        Enum(MatchType, name="match_type"),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[DuplicateStatus] = mapped_column(
        Enum(DuplicateStatus, name="duplicate_status"),
        nullable=False,
        default=DuplicateStatus.PENDING,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    matched_invoice = relationship("Invoice", foreign_keys=[matched_invoice_id])
