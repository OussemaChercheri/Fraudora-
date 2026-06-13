from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.dashboard_service import get_dashboard_summary
from app.services.report_service import generate_dashboard_report_excel, generate_dashboard_report_pdf
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
) -> dict:
    return await get_dashboard_summary(db, current_user, date_from=date_from, date_to=date_to)


@router.get("/export/pdf")
async def export_dashboard_pdf(
    date_from: date,
    date_to: date,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["FINANCE", "ADMIN"]))],
):
    pdf = await generate_dashboard_report_pdf(db, current_user, date_from, date_to)
    return StreamingResponse(
        iter([pdf]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=fraudguard_dashboard_{date_from}_{date_to}.pdf",
        },
    )


@router.get("/export/excel")
async def export_dashboard_excel(
    date_from: date,
    date_to: date,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(["FINANCE", "ADMIN"]))],
):
    xlsx = await generate_dashboard_report_excel(db, current_user, date_from, date_to)
    return StreamingResponse(
        iter([xlsx]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=fraudguard_dashboard_{date_from}_{date_to}.xlsx",
        },
    )
