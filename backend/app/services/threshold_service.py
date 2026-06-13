import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert_threshold import AlertThreshold
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_all_thresholds(db: AsyncSession) -> list[AlertThreshold]:
    result = await db.execute(
        select(AlertThreshold).order_by(AlertThreshold.threshold_key)
    )
    return list(result.scalars().all())


async def get_threshold_value(
    db: AsyncSession,
    key: str,
    default: float,
) -> float:
    result = await db.execute(
        select(AlertThreshold.threshold_value).where(
            AlertThreshold.threshold_key == key
        )
    )
    value = result.scalar_one_or_none()
    return float(value) if value is not None else default


async def update_threshold(
    db: AsyncSession,
    key: str,
    value: float,
    current_user: User,
) -> AlertThreshold:
    result = await db.execute(
        select(AlertThreshold).where(AlertThreshold.threshold_key == key)
    )
    threshold = result.scalar_one_or_none()
    if threshold is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Threshold '{key}' not found",
        )

    threshold.threshold_value = value
    threshold.updated_by_user_id = current_user.id
    await db.flush()
    return threshold
