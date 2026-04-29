from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    is_online: Optional[bool] = None
    last_seen: Optional[datetime] = None

class UserResponse(UserBase):
    id: UUID
    created_at: datetime
    last_seen: datetime
    is_online: bool

    model_config = ConfigDict(from_attributes=True)

from typing import List

class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    size: int
