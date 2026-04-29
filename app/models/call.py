import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import enum
from app.db.base import Base

class CallStatus(str, enum.Enum):
    INITIATED = "initiated"
    RINGING = "ringing"
    CONNECTED = "connected"
    ENDED = "ended"

class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    call_type = Column(String, nullable=False) # voice/video
    status = Column(String, default=CallStatus.INITIATED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
