from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token, RefreshTokenRequest, LoginRequest
from app.core.security import create_access_token, create_refresh_token, verify_password, get_password_hash
from app.core.config import settings
from jose import jwt, JWTError

router = APIRouter()

from app.schemas.common import APIResponse

@router.post("/register", response_model=APIResponse[UserResponse])
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == user_in.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password)
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return APIResponse(
        status=True,
        message="User registered successfully",
        data=user
    )

@router.post("/login", response_model=APIResponse[Token])
async def login(login_in: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == login_in.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_in.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    return APIResponse(
        status=True,
        message="Login successful",
        data={
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
            "username": user.username
        }
    )

@router.post("/refresh", response_model=APIResponse[Token])
async def refresh_token(refresh_in: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = jwt.decode(
            refresh_in.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return APIResponse(
        status=True,
        message="Token refreshed successfully",
        data={
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
            "token_type": "bearer",
            "username": user.username
        }
    )
