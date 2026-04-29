from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user
from uuid import UUID

router = APIRouter()

from app.schemas.common import APIResponse

@router.get("/me", response_model=APIResponse[UserResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return APIResponse(
        status=True,
        message="Profile retrieved",
        data=current_user
    )

@router.get("/{user_id}", response_model=APIResponse[UserResponse])
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return APIResponse(
        status=True,
        message="User retrieved",
        data=user
    )
