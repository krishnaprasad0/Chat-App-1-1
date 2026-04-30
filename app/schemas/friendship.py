from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from enum import Enum

class FriendshipStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class FriendshipBase(BaseModel):
    friend_id: UUID

class FriendshipCreate(FriendshipBase):
    pass

class FriendshipUpdate(BaseModel):
    status: FriendshipStatus

class FriendshipResponse(BaseModel):
    id: UUID
    user_id: UUID
    friend_id: UUID
    status: FriendshipStatus
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

from app.schemas.user import UserResponse

class FriendListResponse(BaseModel):
    friends: List[UserResponse]

class PendingRequestResponse(BaseModel):
    id: UUID
    sender: UserResponse
    created_at: datetime
