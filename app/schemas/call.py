from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from app.models.call import CallStatus

class CallBase(BaseModel):
    receiver_id: UUID
    call_type: str # voice/video

class CallCreate(CallBase):
    pass

class CallUpdate(BaseModel):
    status: CallStatus

class CallResponse(CallBase):
    id: UUID
    caller_id: UUID
    status: CallStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
