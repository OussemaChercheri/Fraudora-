from dataclasses import dataclass
from datetime import date
from typing import Literal, Optional

from app.models.invoice import FileType, InvoiceStatus


@dataclass
class InvoiceFilters:
    status: Optional[InvoiceStatus] = None
    file_type: Optional[FileType] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    has_duplicate_alert: Optional[bool] = None
    has_anomaly_alert: Optional[bool] = None
    sort_by: Literal["created_at", "original_filename", "file_size_kb"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = 20
