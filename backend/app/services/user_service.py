import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password

logger = logging.getLogger(__name__)


async def _get_user_or_404(db: AsyncSession, user_id: UUID) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


async def create_user(db: AsyncSession, user_create: UserCreate) -> User:
    existing = await db.execute(select(User).where(User.email == user_create.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=user_create.email,
        full_name=user_create.full_name,
        role=user_create.role,
        hashed_password=hash_password(user_create.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "[EMAIL PLACEHOLDER] Confirmation email would be sent to %s",
        user.email,
    )

    return user


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
    return await _get_user_or_404(db, user_id)


async def get_all_users(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def update_user(
    db: AsyncSession,
    user_id: UUID,
    user_update: UserUpdate,
) -> User:
    user = await _get_user_or_404(db, user_id)
    update_data = user_update.model_dump(exclude_unset=True)

    if "email" in update_data and update_data["email"] != user.email:
        existing = await db.execute(
            select(User).where(User.email == update_data["email"])
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


async def deactivate_user(db: AsyncSession, user_id: UUID) -> User:
    user = await _get_user_or_404(db, user_id)
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user_id: UUID) -> None:
    user = await _get_user_or_404(db, user_id)
    await db.delete(user)
    await db.commit()
