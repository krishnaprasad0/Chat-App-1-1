from fastapi import WebSocket
from typing import Dict, List, Optional
import redis.asyncio as redis
from app.core.config import settings
from app.services.notification_service import notification_service
import json
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Local connections on THIS server instance
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = None

    async def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id] = websocket
        # Track globally online users
        await self.redis.sadd("online_users", user_id)

    async def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        # Remove from globally online users
        await self.redis.srem("online_users", user_id)

    async def send_personal_message(self, message: dict, user_id: str, db: Optional[AsyncSession] = None):
        # 1. Check if user is connected to THIS instance
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
            return

        # 2. Check if user is connected to ANY instance
        is_online = await self.redis.sismember("online_users", user_id)
        if is_online:
            # Relay to the instance where the user is connected
            await self.redis.publish(f"user_channel:{user_id}", json.dumps(message))
        else:
            # 3. User is offline - Send Push Notification
            logger.info(f"User {user_id} is offline. Triggering push notification fallback.")
            if db:
                await self._trigger_push_notification(message, user_id, db)
            else:
                logger.warning(f"Cannot send push notification for {user_id}: DB session not provided.")

    async def _trigger_push_notification(self, message: dict, user_id: str, db: AsyncSession):
        try:
            # Get receiver info
            from uuid import UUID
            uid = UUID(user_id) if isinstance(user_id, str) else user_id
            result = await db.execute(select(User).where(User.id == uid))
            receiver = result.scalar_one_or_none()
            
            if receiver and receiver.fcm_token:
                # Get sender info to show a friendly name
                sender_id = message.get("sender_id")
                sender_name = "New Message"
                if sender_id:
                    sender_result = await db.execute(select(User).where(User.id == UUID(sender_id)))
                    sender = sender_result.scalar_one_or_none()
                    if sender:
                        sender_name = sender.username
                
                # Determine message type for better notification text
                msg_type = message.get("message_type", "text")
                if msg_type == "image":
                    body = f"📷 {sender_name} sent you an image"
                elif msg_type == "video":
                    body = f"🎥 {sender_name} sent you a video"
                elif msg_type == "voice":
                    body = f"🎤 {sender_name} sent you a voice message"
                else:
                    body = f"💬 {sender_name} sent you a message"
                
                logger.info(f"Sending FCM notification to user {user_id} ({receiver.username})")
                await notification_service.send_push_notification(
                    token=receiver.fcm_token,
                    title=sender_name,
                    body=body,
                    data={
                        "type": "chat_message",
                        "sender_id": str(sender_id) if sender_id else "",
                        "message_id": str(message.get("id", ""))
                    }
                )
            else:
                logger.warning(f"Skipping push notification for {user_id}: User not found or has no FCM token.")
        except Exception as e:
            logger.error(f"Error in _trigger_push_notification: {e}", exc_info=True)

    async def listen_redis(self):
        pubsub = self.redis.pubsub()
        await pubsub.psubscribe("user_channel:*")
        
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"]
                user_id = channel.split(":")[-1]
                data = json.loads(message["data"])
                
                if user_id in self.active_connections:
                    await self.active_connections[user_id].send_json(data)

manager = ConnectionManager()
