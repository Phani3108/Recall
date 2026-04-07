from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import User, OrgMembership
from app.api.deps import get_current_user
from app.api.schemas import UserResponse, UserUpdate

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    updates: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    if updates.name is not None:
        user.name = updates.name
    if updates.avatar_url is not None:
        user.avatar_url = updates.avatar_url
    db.add(user)
    await db.flush()
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
    )


@router.delete("/me", status_code=204)
async def delete_account(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(OrgMembership).where(OrgMembership.user_id == user.id)
    )
    user.is_active = False
    user.email = f"deleted_{user.id}@deleted.recall.dev"
    db.add(user)
    await db.flush()
    return None
