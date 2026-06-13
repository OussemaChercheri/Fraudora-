from datetime import datetime
from math import ceil
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.invoice import FileType, InvoiceStatus


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    original_filename: str
    file_type: FileType
    file_size_kb: int
    status: InvoiceStatus
    error_message: Optional[str] = None
    ocr_page_count: Optional[int] = None
    ocr_processing_time_ms: Optional[int] = None
    has_duplicate_alert: bool = False
    is_duplicate_confirmed: bool = False
    has_anomaly_alert: bool = False
    created_at: datetime


class InvoiceDetailResponse(InvoiceResponse):
    ocr_raw_text: Optional[str] = None


class InvoiceListResponse(BaseModel):
    items: list[InvoiceResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkUploadItemResult(BaseModel):
    filename: str
    status: str
    invoice_id: Optional[UUID] = None
    error_message: Optional[str] = None


class BulkUploadResponse(BaseModel):
    results: list[BulkUploadItemResult]
