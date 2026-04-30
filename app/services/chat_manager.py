from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message, MessageStatus
from app.websocket.connection_manager import manager
from app.services.presence_manager import presence_manager
from app.models.friendship import Friendship, FriendshipStatus
from sqlalchemy import select, or_, and_
from uuid import UUID
import json

from app.core.encryption import encryptor

class ChatManager:
    @staticmethod
    async def handle_message(db: AsyncSession, sender_id: UUID, data: dict):
        # data format: {receiver_id, encrypted_content, message_type, media_url}
        receiver_id = UUID(data["receiver_id"])
        
        # 0. Check Friendship Status (E2E Privacy & Policy)
        friend_query = select(Friendship).where(
            and_(
                or_(
                    and_(Friendship.user_id == sender_id, Friendship.friend_id == receiver_id),
                    and_(Friendship.user_id == receiver_id, Friendship.friend_id == sender_id)
                ),
                Friendship.status == FriendshipStatus.ACCEPTED
            )
        )
        friend_result = await db.execute(friend_query)
        if not friend_result.scalar_one_or_none():
            # Not friends, don't allow message
            print(f"DEBUG: Blocking message from {sender_id} to {receiver_id} - NOT FRIENDS")
            return None

        # 1. Store in DB
        original_content = data["encrypted_content"]
        # Encrypt ALL content (text, media URLs, etc.) for maximum privacy
        db_content = encryptor.encrypt(original_content)
        
        db_message = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            encrypted_content=db_content,
            message_type=data.get("message_type", "text"),
            media_url=data.get("media_url"),
            duration=data.get("duration")
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
            "duration": db_message.duration,
            "created_at": db_message.created_at.isoformat(),
            "status": db_message.status
        }
        
        await manager.send_personal_message(message_payload, str(receiver_id), db=db)
        
        return db_message

    @staticmethod
    async def update_status(db: AsyncSession, message_id: UUID, status: str):
        # 1. Update status in DB
        from sqlalchemy import select
        result = await db.execute(select(Message).where(Message.id == message_id))
        db_message = result.scalar_one_or_none()
        
        if not db_message:
            return

        # Don't downgrade status (e.g., if already 'seen', don't set to 'delivered')
        status_priority = {"sent": 1, "delivered": 2, "seen": 3}
        if status_priority.get(status, 0) <= status_priority.get(db_message.status, 0):
            return

        db_message.status = status
        await db.commit()

        # 2. Notify the original sender
        status_update = {
            "type": "message_status_update",
            "message_id": str(message_id),
            "status": status,
            "receiver_id": str(db_message.receiver_id)
        }
        await manager.send_personal_message(status_update, str(db_message.sender_id), db=db)
