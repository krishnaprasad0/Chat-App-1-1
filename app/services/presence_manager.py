import redis.asyncio as redis
from app.core.config import settings
from datetime import datetime, timezone
import json

class PresenceManager:
    def __init__(self):
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

    async def set_online(self, user_id: str):
        await self.redis.set(f"presence:{user_id}", "online")
        await self.redis.set(f"last_seen:{user_id}", datetime.now(timezone.utc).isoformat())
        # Broadcast status change (optional)
        await self.redis.publish("presence_updates", json.dumps({"user_id": user_id, "status": "online"}))

    async def set_offline(self, user_id: str):
        await self.redis.delete(f"presence:{user_id}")
        await self.redis.set(f"last_seen:{user_id}", datetime.now(timezone.utc).isoformat())
        await self.redis.publish("presence_updates", json.dumps({"user_id": user_id, "status": "offline"}))

    async def get_status(self, user_id: str) -> dict:
        status = await self.redis.get(f"presence:{user_id}") or "offline"
        last_seen = await self.redis.get(f"last_seen:{user_id}")
        return {"status": status, "last_seen": last_seen}

presence_manager = PresenceManager()
