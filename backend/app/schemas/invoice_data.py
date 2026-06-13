from datetime import date, datetime
from typing import Any, Optional, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CorrectionEntry(BaseModel):
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    corrected_by_user_id: str
    corrected_by_name: str
    corrected_at: str


class InvoiceDataFieldStr(BaseModel):
    value: Optional[str] = None
    confidence: float = 0.0
    needs_review: bool = False


class InvoiceDataFieldDate(BaseModel):
    value: Optional[date] = None
    confidence: float = 0.0
    needs_review: bool = False


class InvoiceDataFieldAmount(BaseModel):
    value: Optional[float] = None
    confidence: float = 0.0
    needs_review: bool = False


class InvoiceDataResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    invoice_id: UUID
    invoice_number: InvoiceDataFieldStr
    invoice_date: InvoiceDataFieldDate
    supplier_name: InvoiceDataFieldStr
    total_amount: InvoiceDataFieldAmount
    tax_amount: InvoiceDataFieldAmount
    is_manually_corrected: bool
    correction_history: list[CorrectionEntry]
    created_at: datetime
    updated_at: datetime


class InvoiceDataUpdate(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    supplier_name: Optional[str] = None
    total_amount: Optional[float] = Field(default=None, ge=0)
    tax_amount: Optional[float] = Field(default=None, ge=0)


class FieldConfidence(BaseModel):
    value: Optional[Union[str, float, date]] = None
    confidence: float = 0.0
    needs_review: bool = False


class InvoiceDataConfidenceResponse(BaseModel):
    invoice_number: FieldConfidence
    invoice_date: FieldConfidence
    supplier_name: FieldConfidence
    total_amount: FieldConfidence
    tax_amount: FieldConfidence


class CorrectionHistoryResponse(BaseModel):
    corrections: list[CorrectionEntry]
