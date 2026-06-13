from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.services.email_service import send_daily_summaries
from app.utils.seed_demo_data import seed_demo

router = APIRouter(prefix="/api/v1/dev", tags=["dev"])


@router.post("/seed")
async def seed_demo_data(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if settings.ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seed endpoint is only available when ENV=development",
        )

    await seed_demo(db)
    return {"seeded": True, "message": "Demo data created"}


@router.post("/trigger-daily-email")
async def trigger_daily_email(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if settings.ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trigger endpoint is only available when ENV=development",
        )

    count = await send_daily_summaries(db)
    await db.commit()
    return {"sent": count}
