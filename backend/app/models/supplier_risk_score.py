import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SupplierRiskScore(Base):
    __tablename__ = "supplier_risk_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    supplier_name: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_invoices: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_amount_sum: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    avg_amount: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    std_amount: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    anomaly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    first_seen_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
