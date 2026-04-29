from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db.session import get_db
from app.models.message import Message
from app.schemas.message import MessageResponse
from app.core.dependencies import get_current_user
from app.models.user import User
from uuid import UUID
from typing import List

router = APIRouter()

from app.schemas.common import APIResponse

@router.get("/{user_id}", response_model=APIResponse[List[MessageResponse]])
async def get_chat_history(
    user_id: UUID, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Fetch messages between current_user and user_id
    query = select(Message).where(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == user_id),
            and_(Message.sender_id == user_id, Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc())
    
    result = await db.execute(query)
    messages = result.scalars().all()
    
    from app.core.encryption import encryptor
    # Decrypt messages for the client (which expect E2EE blobs)
    for msg in messages:
        msg.encrypted_content = encryptor.decrypt(msg.encrypted_content)
        
    return APIResponse(
        status=True,
        message="Chat history retrieved",
        data=messages
    )
