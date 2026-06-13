from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.duplicate_match import DuplicateStatus, MatchType


class InvoiceSummary(BaseModel):
    id: UUID
    original_filename: str
    invoice_number: Optional[str] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = None
    invoice_date: Optional[date] = None


class DuplicateMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    matched_invoice_id: UUID
    match_type: MatchType
    similarity_score: float
    status: DuplicateStatus
    rejection_reason: Optional[str] = None
    reviewed_by_user_id: Optional[UUID] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    invoice: InvoiceSummary
    matched_invoice: InvoiceSummary


class DuplicateReviewRequest(BaseModel):
    status: str
    rejection_reason: Optional[str] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in ("CONFIRMED_DUPLICATE", "REJECTED"):
            raise ValueError('status must be "CONFIRMED_DUPLICATE" or "REJECTED"')
        return v

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v: Optional[str], info) -> Optional[str]:
        status = info.data.get("status")
        if status == "REJECTED":
            if not v or not v.strip():
                raise ValueError("rejection_reason is required when status is REJECTED")
            return v.strip()
        return v
