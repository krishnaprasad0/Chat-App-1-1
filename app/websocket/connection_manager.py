from fastapi import WebSocket
from typing import Dict, List
import redis.asyncio as redis
from app.core.config import settings
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        # Local connections on THIS server instance
        self.active_connections: Dict[str, WebSocket] = {}
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.pubsub = None

    async def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)
        else:
            # If not on this instance, publish to Redis so other instances can handle it
            await self.redis.publish(f"user_channel:{user_id}", json.dumps(message))

    async def broadcast(self, message: dict):
        # Local broadcast
        for connection in self.active_connections.values():
            await connection.send_json(message)
        # Global broadcast via Redis
        await self.redis.publish("global_chat", json.dumps(message))

    async def subscribe_to_user_events(self):
        """
        Background task to listen for messages from Redis and push to local WebSockets.
        """
        self.pubsub = self.redis.pubsub()
        # In a real scaled app, we'd subscribe to user_channel:{instance_id} or similar
        # For simplicity, we'll listen to all user channels or use a pattern
        # Here we just show the logic for listening to user-specific messages
        pass 

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
