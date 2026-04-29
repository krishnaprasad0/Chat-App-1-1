from app.websocket.connection_manager import manager
from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

class SignalingManager:
    @staticmethod
    async def relay_signal(sender_id: UUID, data: dict, db: Optional[AsyncSession] = None):
        # data format: {receiver_id, type: "offer"|"answer"|"ice", payload: ...}
        receiver_id = data.get("receiver_id")
        if not receiver_id:
            return

        payload = {
            "type": f"call_{data['type']}",
            "sender_id": str(sender_id),
            "data": data["payload"]
        }
        
        await manager.send_personal_message(payload, str(receiver_id), db=db)
