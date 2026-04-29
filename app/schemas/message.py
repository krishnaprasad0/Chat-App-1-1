from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.message import MessageType, MessageStatus

class MessageBase(BaseModel):
    receiver_id: UUID
    encrypted_content: str
    message_type: MessageType = MessageType.TEXT
    media_url: Optional[str] = None

class MessageCreate(MessageBase):
    pass

class MessageUpdate(BaseModel):
    status: MessageStatus

class MessageResponse(MessageBase):
    id: UUID
    sender_id: UUID
    status: MessageStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
