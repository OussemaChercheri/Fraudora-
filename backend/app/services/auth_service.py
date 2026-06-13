import logging
import secrets
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


def _token_data(user: User) -> dict:
    return {
        "sub": str(user.id),
        "email": user.email,
        "role": user.role.value,
    }


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def login(db: AsyncSession, email: str, password: str) -> dict[str, str]:
    user = await authenticate_user(db, email, password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    data = _token_data(user)
    return {
        "access_token": create_access_token(data),
        "refresh_token": create_refresh_token({"sub": str(user.id)}),
        "token_type": "bearer",
    }


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> dict[str, str]:
    payload = decode_token(refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await db.execute(select(User).where(User.id == UUID(str(user_id))))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    return {
        "access_token": create_access_token(_token_data(user)),
        "token_type": "bearer",
    }


async def create_password_reset_token(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        return

    token_value = secrets.token_urlsafe(32)
    reset_token = PasswordResetToken(user_id=user.id, token=token_value)
    db.add(reset_token)
    await db.commit()

    logger.info(
        "[PASSWORD RESET PLACEHOLDER] Reset token for %s: %s (expires in 1h)",
        user.email,
        token_value,
    )


async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str,
) -> None:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None or reset_token.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = hash_password(new_password)
    reset_token.used = True
    await db.commit()
