from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse
from app.services import notification_service
from app.utils.dependencies import get_current_user

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/", response_model=NotificationListResponse)
async def list_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
) -> NotificationListResponse:
    return await notification_service.get_notifications(
        db, current_user.id, page=page, page_size=page_size, unread_only=unread_only,
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def read_notification(
    notification_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Notification:
    from uuid import UUID
    result = await notification_service.mark_notification_read(
        db, UUID(notification_id), current_user.id,
    )
    await db.commit()
    return result


@router.put("/read-all")
async def read_all_notifications(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    count = await notification_service.mark_all_read(db, current_user.id)
    await db.commit()
    return {"updated": count, "message": f"{count} notifications marquées comme lues"}
