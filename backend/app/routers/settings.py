from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.alert_threshold import AlertThresholdResponse, AlertThresholdUpdate
from app.services import threshold_service
from app.utils.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

admin_only = Depends(require_role(["ADMIN"]))


@router.get("/thresholds", response_model=list[AlertThresholdResponse])
async def list_thresholds(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, admin_only],
) -> list[AlertThreshold]:
    return await threshold_service.get_all_thresholds(db)


@router.put("/thresholds/{key}", response_model=AlertThresholdResponse)
async def modify_threshold(
    key: str,
    body: AlertThresholdUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, admin_only],
) -> AlertThreshold:
    result = await threshold_service.update_threshold(db, key, body.threshold_value, current_user)
    await db.commit()
    return result
