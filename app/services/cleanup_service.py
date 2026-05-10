from datetime import datetime, timedelta, timezone
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.message import Message
from app.services.s3_service import s3_service
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class CleanupService:
    @staticmethod
    async def cleanup_old_messages(db: AsyncSession):
        """
        Deletes messages and associated media older than their expiry time.
        """
        try:
            # Current time
            now = datetime.now(timezone.utc)
            
            # Legacy threshold (for messages created before this update)
            legacy_threshold = now - timedelta(hours=settings.MESSAGE_VALIDITY_HOURS)
            
            # 1. Find messages to delete
            # Delete if expires_at has passed OR if it's a legacy message (no expires_at) and past default threshold
            query = select(Message).where(
                or_(
                    Message.expires_at < now,
                    and_(Message.expires_at == None, Message.created_at < legacy_threshold)
                )
            )
            result = await db.execute(query)
            messages_to_delete = result.scalars().all()
            
            if not messages_to_delete:
                return 0

            count = len(messages_to_delete)
            logger.info(f"Starting cleanup for {count} expired messages.")

            for msg in messages_to_delete:
                # 2. Delete media from S3 if exists
                if msg.media_url:
                    # s3_service.delete_file handles both full URLs and keys
                    await s3_service.delete_file(msg.media_url)
                
                # 3. Delete from DB
                await db.delete(msg)
            
            await db.commit()
            logger.info(f"Successfully cleaned up {count} messages.")
            return count

        except Exception as e:
            logger.error(f"Error during message cleanup: {e}")
            await db.rollback()
            return 0
