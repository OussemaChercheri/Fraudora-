from datetime import date, datetime
from io import BytesIO
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.analysis import (
    MonthlyVolumeItem,
    OcrQualityStatsResponse,
    ProcessingSummaryResponse,
    StatusBreakdown,
    SupplierSummaryItem,
)
from app.services import analysis_service, report_service
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])

analysis_access = Depends(require_role(["COMPTABLE", "FINANCE", "ADMIN"]))
report_access = Depends(require_role(["FINANCE", "ADMIN"]))


def _resolve_user_filter(current_user: User) -> Optional[UUID]:
    if current_user.role in {UserRole.ADMIN, UserRole.FINANCE}:
        return None
    if current_user.role == UserRole.COMPTABLE:
        return current_user.id
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient permissions",
    )


@router.get("/summary", response_model=ProcessingSummaryResponse)
async def processing_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, analysis_access],
) -> ProcessingSummaryResponse:
    user_id = _resolve_user_filter(current_user)
    data = await analysis_service.get_processing_summary(db, user_id)
    return ProcessingSummaryResponse(
        total_invoices=data["total_invoices"],
        by_status=StatusBreakdown(**data["by_status"]),
        processed_rate=data["processed_rate"],
        review_required_rate=data["review_required_rate"],
        error_rate=data["error_rate"],
        avg_processing_time_ms=data["avg_processing_time_ms"],
        total_pages_processed=data["total_pages_processed"],
    )


@router.get("/ocr-quality", response_model=OcrQualityStatsResponse)
async def ocr_quality_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, analysis_access],
) -> OcrQualityStatsResponse:
    user_id = _resolve_user_filter(current_user)
    data = await analysis_service.get_ocr_quality_stats(db, user_id)
    return OcrQualityStatsResponse(**data)


@router.get("/suppliers", response_model=list[SupplierSummaryItem])
async def supplier_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, analysis_access],
) -> list[SupplierSummaryItem]:
    user_id = _resolve_user_filter(current_user)
    data = await analysis_service.get_supplier_summary(db, user_id)
    return [SupplierSummaryItem(**item) for item in data]


@router.get("/monthly-volume", response_model=list[MonthlyVolumeItem])
async def monthly_volume(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, analysis_access],
    months: int = Query(6, ge=1, le=24),
) -> list[MonthlyVolumeItem]:
    user_id = _resolve_user_filter(current_user)
    data = await analysis_service.get_monthly_volume(db, months=months, user_id=user_id)
    return [MonthlyVolumeItem(**item) for item in data]


@router.get("/report/pdf")
async def download_report_pdf(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, report_access],
) -> StreamingResponse:
    pdf_bytes = await report_service.generate_pilot_report_pdf(db, user_id=None)
    date_str = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="fraudguard_rapport_{date_str}.pdf"'
        },
    )


@router.get("/report/excel")
async def download_report_excel(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, report_access],
) -> StreamingResponse:
    excel_bytes = await report_service.generate_pilot_report_excel(db, user_id=None)
    date_str = datetime.now().strftime("%Y%m%d")
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="fraudguard_rapport_{date_str}.xlsx"'
        },
    )


@router.get("/expense-evolution")
async def expense_evolution(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, analysis_access],
    date_from: date = Query(...),
    date_to: date = Query(...),
    granularity: str = Query("month", pattern="^(day|week|month)$"),
) -> dict:
    user_id = _resolve_user_filter(current_user)
    result = await analysis_service.get_expense_evolution(
        db, current_user, date_from, date_to, granularity,
    )
    return result
