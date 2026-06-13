from datetime import date
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.duplicate_match import DuplicateMatchResponse, DuplicateReviewRequest
from app.services import duplicate_service
from app.services.report_service import generate_duplicates_report_excel, generate_duplicates_report_pdf
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/duplicates", tags=["duplicates"])

reviewer = Depends(require_role(["COMPTABLE", "FINANCE", "ADMIN"]))


@router.get("/invoice/{invoice_id}", response_model=list[DuplicateMatchResponse])
async def list_duplicate_matches(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DuplicateMatchResponse]:
    return await duplicate_service.get_duplicate_matches(db, invoice_id, current_user)


@router.get("/invoice/{invoice_id}/summary")
async def duplicate_summary(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    return await duplicate_service.get_duplicate_summary_for_invoice(
        db, invoice_id, current_user
    )


@router.put("/{match_id}/review", response_model=DuplicateMatchResponse)
async def review_match(
    match_id: UUID,
    body: DuplicateReviewRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, reviewer],
) -> DuplicateMatchResponse:
    result = await duplicate_service.review_duplicate_match(
        db, match_id, body, current_user
    )
    await db.commit()
    return result


@router.get("/pending", response_model=dict)
async def list_pending_matches(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    items, total, total_pages = await duplicate_service.get_pending_matches_paginated(
        db, current_user, page=page, page_size=page_size
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/report/pdf")
async def duplicates_report_pdf(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["FINANCE", "ADMIN"]))],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    pdf = await generate_duplicates_report_pdf(db, current_user, date_from, date_to)
    f_from = date_from or "debut"
    f_to = date_to or "fin"
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=fraudguard_doublons_{f_from}_{f_to}.pdf",
        },
    )


@router.get("/report/excel")
async def duplicates_report_excel(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["FINANCE", "ADMIN"]))],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
):
    xlsx = await generate_duplicates_report_excel(db, current_user, date_from, date_to)
    f_from = date_from or "debut"
    f_to = date_to or "fin"
    return StreamingResponse(
        iter([xlsx]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=fraudguard_doublons_{f_from}_{f_to}.xlsx",
        },
    )
