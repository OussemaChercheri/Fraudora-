import logging
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User, UserRole
from app.schemas.notification import NotificationListResponse, NotificationResponse

logger = logging.getLogger(__name__)


async def get_finance_and_admin_user_ids(db: AsyncSession) -> list[UUID]:
    result = await db.execute(
        select(User.id).where(
            User.role.in_([UserRole.FINANCE, UserRole.ADMIN]),
            User.is_active.is_(True),
        )
    )
    return [row[0] for row in result.all()]


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str,
    related_invoice_id: UUID | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=NotificationType(notification_type),
        related_invoice_id=related_invoice_id,
    )
    db.add(notification)
    await db.flush()
    return notification


async def get_notifications(
    db: AsyncSession,
    user_id: UUID,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
) -> NotificationListResponse:
    conditions = [Notification.user_id == user_id]
    if unread_only:
        conditions.append(Notification.is_read.is_(False))

    total_result = await db.execute(
        select(func.count()).select_from(Notification).where(*conditions)
    )
    total = total_result.scalar() or 0

    unread_result = await db.execute(
        select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    )
    unread_count = unread_result.scalar() or 0

    offset = (page - 1) * page_size
    items_result = await db.execute(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    items = [NotificationResponse.model_validate(n) for n in items_result.scalars().all()]

    return NotificationListResponse(
        items=items,
        unread_count=unread_count,
        total=total,
    )


async def mark_notification_read(
    db: AsyncSession,
    notification_id: UUID,
    user_id: UUID,
) -> Notification:
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()
    if notification is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    await db.flush()
    return notification


async def mark_all_read(
    db: AsyncSession,
    user_id: UUID,
) -> int:
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.flush()
    return result.rowcount
