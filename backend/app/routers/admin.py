from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.dependencies import require_role
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])

admin_required = Depends(require_role(["ADMIN"]))


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_create: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
) -> User:
    return await user_service.create_user(db, user_create)


@router.get("/", response_model=list[UserResponse])
async def get_all_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
    skip: int = 0,
    limit: int = 100,
) -> list[User]:
    return await user_service.get_all_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
) -> User:
    return await user_service.get_user_by_id(db, user_id)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
) -> User:
    return await user_service.update_user(db, user_id, user_update)


@router.delete("/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
) -> User:
    return await user_service.deactivate_user(db, user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, admin_required],
) -> None:
    await user_service.delete_user(db, user_id)
