import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AlertType(str, enum.Enum):
    ABNORMAL_AMOUNT = "ABNORMAL_AMOUNT"
    NEW_HIGH_RISK_SUPPLIER = "NEW_HIGH_RISK_SUPPLIER"
    PRICE_SPIKE = "PRICE_SPIKE"


class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    DISMISSED = "DISMISSED"


class AnomalyAlert(Base):
    __tablename__ = "anomaly_alerts"

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
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type"),
        nullable=False,
    )
    severity: Mapped[Severity] = mapped_column(
        Enum(Severity, name="severity"),
        nullable=False,
        default=Severity.MEDIUM,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus, name="alert_status"),
        nullable=False,
        default=AlertStatus.PENDING,
    )
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    invoice = relationship("Invoice", foreign_keys=[invoice_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_user_id])
