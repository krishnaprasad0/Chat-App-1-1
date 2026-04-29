import firebase_admin
from firebase_admin import credentials, messaging
import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.initialized = False
        try:
            # Look for service account in environment or local file
            cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "app/credentials/service_account.json")
            if os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                logger.info("Firebase Admin initialized successfully.")
            else:
                logger.warning(f"Firebase credentials not found at {cred_path}. Push notifications will be disabled.")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin: {e}")

    async def send_push_notification(
        self, 
        token: str, 
        title: str, 
        body: str, 
        data: Optional[dict] = None
    ):
        if not self.initialized:
            logger.warning("Attempted to send notification but Firebase is not initialized.")
            return

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Successfully sent push notification: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending push notification: {e}")
            return None

notification_service = NotificationService()
