from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.anomaly_alert import AlertType, Severity
from app.models.user import User
from app.schemas.anomaly_alert import (
    AnomalyAlertResponse,
    AnomalyAcknowledgeRequest,
    SupplierRiskScoreResponse,
)
from app.services import anomaly_service
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])

reviewer = Depends(require_role(["COMPTABLE", "FINANCE", "ADMIN"]))
risk_viewer = Depends(require_role(["FINANCE", "ADMIN"]))
admin_only = Depends(require_role(["ADMIN"]))


@router.get("/invoice/{invoice_id}", response_model=list[AnomalyAlertResponse])
async def list_anomaly_alerts(
    invoice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[AnomalyAlertResponse]:
    return await anomaly_service.get_anomaly_alerts(db, invoice_id, current_user)


@router.put("/{alert_id}/review", response_model=AnomalyAlertResponse)
async def review_anomaly_alert(
    alert_id: UUID,
    body: AnomalyAcknowledgeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, reviewer],
) -> AnomalyAlertResponse:
    result = await anomaly_service.acknowledge_anomaly_alert(
        db, alert_id, body, current_user
    )
    await db.commit()
    return result


@router.get("/pending")
async def list_pending_anomalies(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    alert_type: Optional[AlertType] = None,
    severity: Optional[Severity] = None,
) -> dict:
    items, total, total_pages = await anomaly_service.get_pending_anomalies(
        db, current_user, page=page, page_size=page_size,
        alert_type=alert_type, severity=severity,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/suppliers/risk-scores", response_model=list[SupplierRiskScoreResponse])
async def list_supplier_risk_scores(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, risk_viewer],
    min_risk_score: Optional[int] = Query(None, ge=0, le=100),
) -> list[SupplierRiskScoreResponse]:
    return await anomaly_service.get_supplier_risk_scores(
        db, current_user, min_risk_score=min_risk_score,
    )


@router.post("/suppliers/recompute")
async def recompute_risk_scores(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, admin_only],
) -> dict:
    count = await anomaly_service.recompute_all_supplier_risk_scores(db)
    await db.commit()
    return {"recomputed": count, "message": f"Risk scores recomputed for {count} suppliers"}
