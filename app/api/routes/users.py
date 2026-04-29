from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user
from uuid import UUID

from app.schemas.user import UserResponse, PaginatedUserResponse
from sqlalchemy import func

router = APIRouter()

from app.schemas.common import APIResponse

@router.get("/", response_model=APIResponse[PaginatedUserResponse])
async def get_users(
    page: int = 1,
    size: int = 10,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * size
    
    # Get total count
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar()
    
    # Get items
    result = await db.execute(
        select(User)
        .order_by(User.username.asc())
        .offset(offset)
        .limit(size)
    )
    users = result.scalars().all()
    
    return APIResponse(
        status=True,
        message="Users retrieved",
        data=PaginatedUserResponse(
            items=users,
            total=total,
            page=page,
            size=size
        )
    )

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
