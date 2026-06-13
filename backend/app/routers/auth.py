from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services import auth_service
from app.models.user import User
from app.utils.dependencies import get_current_user, oauth2_scheme
from app.utils.security import token_blacklist

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    return await auth_service.login(db, form_data.username, form_data.password)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    body: RefreshTokenRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    return await auth_service.refresh_access_token(db, body.refresh_token)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)],
    _: Annotated[User, Depends(get_current_user)],
) -> dict[str, str]:
    token_blacklist.add(token)
    return {"message": "Successfully logged out"}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.create_password_reset_token(db, body.email)
    return {
        "message": "If the email exists, a password reset link has been sent",
    }


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    await auth_service.reset_password(db, body.token, body.new_password)
    return {"message": "Password has been reset successfully"}
