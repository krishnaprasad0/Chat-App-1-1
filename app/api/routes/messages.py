from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from app.db.session import get_db
from app.models.message import Message
from app.schemas.message import MessageResponse
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.s3_service import s3_service
import os
import uuid
from typing import List
from uuid import UUID

from app.core.encryption import encryptor

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
    
    # Decrypt text messages for the client (media URLs should NOT be decrypted)
    for msg in messages:
        if msg.message_type == "text":
            msg.encrypted_content = encryptor.decrypt(msg.encrypted_content)
        
    return APIResponse(
        status=True,
        message="Chat history retrieved",
        data=messages
    )

@router.post("/upload")
async def upload_media(
    receiver_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    try:
        # Read file content
        file_content = await file.read()
        
        # Unique file name
        ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        # Organize in folders: media/sender_id/receiver_id/filename
        prefix = f"media/{current_user.id}/{receiver_id}"
        
        # Upload to S3 (encrypted by default in S3Service)
        url = await s3_service.upload_file(
            file_data=file_content,
            file_name=unique_filename,
            content_type=file.content_type,
            prefix=prefix,
            encrypt=False
        )
        
        if not url:
            raise HTTPException(status_code=500, detail="Failed to upload file")
            
        return APIResponse(
            status=True,
            message="File uploaded successfully",
            data={"url": url, "filename": unique_filename}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

