from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.anomaly_alert import AlertStatus, AlertType, Severity


class InvoiceSummary(BaseModel):
    id: UUID
    original_filename: str
    invoice_number: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_date: Optional[date] = None


class AnomalyAlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    alert_type: AlertType
    severity: Severity
    description: str
    metric_value: float
    threshold_value: float
    status: AlertStatus
    acknowledged_by_user_id: Optional[UUID] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    invoice: InvoiceSummary


class AnomalyAcknowledgeRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("ACKNOWLEDGED", "DISMISSED"):
            raise ValueError('status must be "ACKNOWLEDGED" or "DISMISSED"')
        return v


class SupplierRiskScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    supplier_name: str
    risk_score: int
    total_invoices: int
    total_amount_sum: float
    avg_amount: float
    std_amount: float
    anomaly_count: int
    last_invoice_date: Optional[date] = None
    first_seen_date: Optional[date] = None
    updated_at: datetime
