import uuid
from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum
from app.db.base import Base

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"

class MessageStatus(str, enum.Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    SEEN = "seen"

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    encrypted_content = Column(Text, nullable=False)
    message_type = Column(String, default=MessageType.TEXT)
    media_url = Column(String, nullable=True)
    status = Column(String, default=MessageStatus.SENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
