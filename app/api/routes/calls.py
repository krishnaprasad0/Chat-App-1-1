from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.models.call import CallSession, CallStatus
from app.schemas.call import CallCreate, CallResponse, CallUpdate
from app.schemas.common import APIResponse
from app.core.dependencies import get_current_user
from app.services.notification_service import notification_service
from app.websocket.connection_manager import manager
from uuid import UUID

router = APIRouter()

@router.post("/", response_model=APIResponse[CallResponse])
async def initiate_call(
    call_data: CallCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if receiver exists
    result = await db.execute(select(User).where(User.id == call_data.receiver_id))
    receiver = result.scalar_one_or_none()
    
    if not receiver:
        raise HTTPException(status_code=404, detail="Receiver not found")

    # Create call session
    new_call = CallSession(
        caller_id=current_user.id,
        receiver_id=receiver.id,
        call_type=call_data.call_type,
        status=CallStatus.INITIATED
    )
    db.add(new_call)
    await db.commit()
    await db.refresh(new_call)

    # Send push notification if receiver has FCM token
    if receiver.fcm_token:
        await notification_service.send_call_notification(
            token=receiver.fcm_token,
            caller_name=current_user.username,
            call_id=str(new_call.id),
            call_type=new_call.call_type,
            caller_id=str(current_user.id)
        )

    # Notify via WebSocket if they are currently online
    payload = {
        "type": "call_incoming",
        "call_id": str(new_call.id),
        "caller_id": str(current_user.id),
        "caller_name": current_user.username,
        "call_type": new_call.call_type
    }
    await manager.send_personal_message(payload, str(receiver.id), db=db)

    return APIResponse(
        status=True,
        message="Call initiated",
        data=new_call
    )

@router.put("/{call_id}/status", response_model=APIResponse[CallResponse])
async def update_call_status(
    call_id: UUID,
    status_data: CallUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(CallSession).where(CallSession.id == call_id))
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    # Only caller or receiver can update
    if call.caller_id != current_user.id and call.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    call.status = status_data.status
    await db.commit()
    await db.refresh(call)

    # Notify the other party
    other_party_id = call.caller_id if current_user.id == call.receiver_id else call.receiver_id
    
    payload = {
        "type": "call_status_update",
        "call_id": str(call.id),
        "status": str(call.status),
        "updated_by": str(current_user.id)
    }
    await manager.send_personal_message(payload, str(other_party_id), db=db)

    return APIResponse(
        status=True,
        message=f"Call status updated to {call.status}",
        data=call
    )
