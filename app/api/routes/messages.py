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
from fastapi.responses import StreamingResponse
import io
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
    
    # Decrypt all messages for the client (handles legacy plain text gracefully via fallback)
    for msg in messages:
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
        
        # Upload to S3 (Encrypted for privacy)
        url = await s3_service.upload_file(
            file_data=file_content,
            file_name=unique_filename,
            content_type=file.content_type,
            prefix=prefix,
            encrypt=True
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


@router.get("/media/view")
async def view_media(
    key: str,
    current_user: User = Depends(get_current_user)
):
    """
    Securely decrypt and stream media from S3.
    Expects key format: media/sender_id/receiver_id/filename
    """
    try:
        # For security, verify the user is either the sender or receiver
        # Format: media/{sender_id}/{receiver_id}/{filename}
        parts = key.split('/')
        if len(parts) >= 3:
            sender_id = parts[1]
            receiver_id = parts[2]
            if str(current_user.id) not in [sender_id, receiver_id]:
                raise HTTPException(status_code=403, detail="Access denied to this media")

        file_data = await s3_service.download_file(key, decrypt=True)
        if not file_data:
            raise HTTPException(status_code=404, detail="File not found or decryption failed")

        # Detect content type from extension
        ext = os.path.splitext(key)[1].lower()
        content_type = "application/octet-stream"
        if ext in ['.jpg', '.jpeg']: content_type = "image/jpeg"
        elif ext == '.png': content_type = "image/png"
        elif ext == '.mp4': content_type = "video/mp4"
        elif ext in ['.mp3', '.m4a', '.wav']: content_type = "audio/mpeg"
        elif ext == '.webp': content_type = "image/webp"

        return StreamingResponse(io.BytesIO(file_data), media_type=content_type)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
