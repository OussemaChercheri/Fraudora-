from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_data import InvoiceData
from app.models.user import User
from app.schemas.invoice_data import (
    CorrectionEntry,
    CorrectionHistoryResponse,
    FieldConfidence,
    InvoiceDataConfidenceResponse,
    InvoiceDataFieldAmount,
    InvoiceDataFieldDate,
    InvoiceDataFieldStr,
    InvoiceDataResponse,
    InvoiceDataUpdate,
)
from app.services.invoice_service import get_invoice_by_id

CONFIDENCE_THRESHOLD = 0.5

FIELD_CONFIDENCE_MAP = {
    "invoice_number": "confidence_invoice_number",
    "invoice_date": "confidence_invoice_date",
    "supplier_name": "confidence_supplier_name",
    "total_amount": "confidence_total_amount",
    "tax_amount": "confidence_tax_amount",
}

EDITABLE_FIELDS = set(FIELD_CONFIDENCE_MAP.keys())


def _needs_review(confidence: float, value: Any = None) -> bool:
    return confidence < CONFIDENCE_THRESHOLD or value is None


def _serialize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _str_value(value: Any) -> str:
    if value is None:
        return ""
    return str(_serialize_value(value))


async def _fetch_invoice_data(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> InvoiceData:
    await get_invoice_by_id(db, invoice_id, current_user)

    result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    invoice_data = result.scalar_one_or_none()

    if invoice_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice data not found",
        )

    return invoice_data


def to_invoice_data_response(data: InvoiceData) -> InvoiceDataResponse:
    correction_history = [
        CorrectionEntry(**entry) for entry in (data.correction_history or [])
    ]

    total = float(data.total_amount) if data.total_amount is not None else None
    tax = float(data.tax_amount) if data.tax_amount is not None else None

    return InvoiceDataResponse(
        id=data.id,
        invoice_id=data.invoice_id,
        invoice_number=InvoiceDataFieldStr(
            value=data.invoice_number,
            confidence=data.confidence_invoice_number,
            needs_review=_needs_review(
                data.confidence_invoice_number, data.invoice_number
            ),
        ),
        invoice_date=InvoiceDataFieldDate(
            value=data.invoice_date,
            confidence=data.confidence_invoice_date,
            needs_review=_needs_review(
                data.confidence_invoice_date, data.invoice_date
            ),
        ),
        supplier_name=InvoiceDataFieldStr(
            value=data.supplier_name,
            confidence=data.confidence_supplier_name,
            needs_review=_needs_review(
                data.confidence_supplier_name, data.supplier_name
            ),
        ),
        total_amount=InvoiceDataFieldAmount(
            value=total,
            confidence=data.confidence_total_amount,
            needs_review=_needs_review(data.confidence_total_amount, total),
        ),
        tax_amount=InvoiceDataFieldAmount(
            value=tax,
            confidence=data.confidence_tax_amount,
            needs_review=_needs_review(data.confidence_tax_amount, tax),
        ),
        is_manually_corrected=data.is_manually_corrected,
        correction_history=correction_history,
        created_at=data.created_at,
        updated_at=data.updated_at,
    )


def to_confidence_response(data: InvoiceData) -> InvoiceDataConfidenceResponse:
    total = float(data.total_amount) if data.total_amount is not None else None
    tax = float(data.tax_amount) if data.tax_amount is not None else None

    return InvoiceDataConfidenceResponse(
        invoice_number=FieldConfidence(
            value=data.invoice_number,
            confidence=data.confidence_invoice_number,
            needs_review=_needs_review(
                data.confidence_invoice_number, data.invoice_number
            ),
        ),
        invoice_date=FieldConfidence(
            value=data.invoice_date,
            confidence=data.confidence_invoice_date,
            needs_review=_needs_review(
                data.confidence_invoice_date, data.invoice_date
            ),
        ),
        supplier_name=FieldConfidence(
            value=data.supplier_name,
            confidence=data.confidence_supplier_name,
            needs_review=_needs_review(
                data.confidence_supplier_name, data.supplier_name
            ),
        ),
        total_amount=FieldConfidence(
            value=total,
            confidence=data.confidence_total_amount,
            needs_review=_needs_review(data.confidence_total_amount, total),
        ),
        tax_amount=FieldConfidence(
            value=tax,
            confidence=data.confidence_tax_amount,
            needs_review=_needs_review(data.confidence_tax_amount, tax),
        ),
    )


def _all_confidences_above_threshold(data: InvoiceData) -> bool:
    scores = [
        data.confidence_invoice_number,
        data.confidence_invoice_date,
        data.confidence_supplier_name,
        data.confidence_total_amount,
        data.confidence_tax_amount,
    ]
    return all(score >= CONFIDENCE_THRESHOLD for score in scores)


def _critical_fields_present(data: InvoiceData) -> bool:
    return data.invoice_number is not None and data.total_amount is not None


def _re_evaluate_invoice_status(invoice: Invoice, invoice_data: InvoiceData) -> None:
    if _critical_fields_present(invoice_data) and _all_confidences_above_threshold(
        invoice_data
    ):
        invoice.status = InvoiceStatus.PROCESSED
    else:
        invoice.status = InvoiceStatus.REVIEW_REQUIRED


async def get_invoice_data(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> InvoiceData:
    return await _fetch_invoice_data(db, invoice_id, current_user)


async def update_invoice_data(
    db: AsyncSession,
    invoice_id: UUID,
    update: InvoiceDataUpdate,
    current_user: User,
) -> InvoiceData:
    invoice = await get_invoice_by_id(db, invoice_id, current_user)

    result = await db.execute(
        select(InvoiceData).where(InvoiceData.invoice_id == invoice_id)
    )
    invoice_data = result.scalar_one_or_none()

    if invoice_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice data not found",
        )

    update_data = update.model_dump(exclude_unset=True)
    history: list[dict] = list(invoice_data.correction_history or [])
    now = datetime.now(timezone.utc)

    for field, new_value in update_data.items():
        if field not in EDITABLE_FIELDS or new_value is None:
            continue

        old_value = getattr(invoice_data, field)
        if _serialize_value(old_value) == _serialize_value(new_value):
            continue

        history.append(
            {
                "field": field,
                "old_value": _str_value(old_value),
                "new_value": _str_value(new_value),
                "corrected_by_user_id": str(current_user.id),
                "corrected_by_name": current_user.full_name,
                "corrected_at": now.isoformat(),
            }
        )

        setattr(invoice_data, field, new_value)
        setattr(invoice_data, FIELD_CONFIDENCE_MAP[field], 1.0)

    if update_data:
        invoice_data.correction_history = history
        invoice_data.is_manually_corrected = True
        _re_evaluate_invoice_status(invoice, invoice_data)

    await db.commit()
    await db.refresh(invoice_data)
    await db.refresh(invoice)
    return invoice_data


async def get_correction_history(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> CorrectionHistoryResponse:
    invoice_data = await _fetch_invoice_data(db, invoice_id, current_user)
    corrections = [
        CorrectionEntry(**entry) for entry in (invoice_data.correction_history or [])
    ]
    corrections.sort(key=lambda entry: entry.corrected_at, reverse=True)
    return CorrectionHistoryResponse(corrections=corrections)


async def get_invoice_data_confidence(
    db: AsyncSession,
    invoice_id: UUID,
    current_user: User,
) -> InvoiceDataConfidenceResponse:
    invoice_data = await _fetch_invoice_data(db, invoice_id, current_user)
    return to_confidence_response(invoice_data)
