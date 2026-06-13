from datetime import date
from typing import Optional

from pydantic import BaseModel


class StatusBreakdown(BaseModel):
    UPLOADED: int
    PROCESSING: int
    PROCESSED: int
    REVIEW_REQUIRED: int
    ERROR: int


class ProcessingSummaryResponse(BaseModel):
    total_invoices: int
    by_status: StatusBreakdown
    processed_rate: float
    review_required_rate: float
    error_rate: float
    avg_processing_time_ms: float
    total_pages_processed: int


class OcrQualityStatsResponse(BaseModel):
    avg_confidence: dict[str, float]
    field_extraction_rate: dict[str, float]
    manually_corrected_count: int
    manually_corrected_rate: float


class SupplierSummaryItem(BaseModel):
    supplier_name: str
    invoice_count: int
    total_amount_sum: float
    avg_amount: float
    min_amount: float
    max_amount: float
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None


class MonthlyVolumeItem(BaseModel):
    month: str
    count: int
    processed_count: int
