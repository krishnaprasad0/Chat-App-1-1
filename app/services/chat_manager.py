from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message, MessageStatus
from app.websocket.connection_manager import manager
from app.services.presence_manager import presence_manager
from uuid import UUID
import json

from app.core.encryption import encryptor

class ChatManager:
    @staticmethod
    async def handle_message(db: AsyncSession, sender_id: UUID, data: dict):
        # data format: {receiver_id, encrypted_content, message_type, media_url}
        receiver_id = UUID(data["receiver_id"])
        
        # 1. Store in DB (with server-side encryption for data at rest)
        original_content = data["encrypted_content"]
        db_content = encryptor.encrypt(original_content)
        
        db_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            encrypted_content=db_content,
            message_type=data.get("message_type", "text"),
            media_url=data.get("media_url")
        )
        db.add(db_message)
        await db.commit()
        await db.refresh(db_message)

        # 2. Check presence
        presence = await presence_manager.get_status(str(receiver_id))
        
        # 3. Route via WebSocket (relay the original E2EE blob)
        message_payload = {
            "type": "new_message",
            "id": str(db_message.id),
            "sender_id": str(sender_id),
            "encrypted_content": original_content,
            "message_type": db_message.message_type,
            "media_url": db_message.media_url,
            "created_at": db_message.created_at.isoformat(),
            "status": db_message.status
        }
        
        await manager.send_personal_message(message_payload, str(receiver_id))
        
        return db_message

    @staticmethod
    async def update_status(db: AsyncSession, message_id: UUID, status: str):
        # Update in DB and notify sender
        pass 
