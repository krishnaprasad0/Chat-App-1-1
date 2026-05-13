try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    # Mock classes to avoid name errors in the class definition
    class messaging:
        class Message: pass
        class Notification: pass
        class AndroidConfig: pass
        class APNSConfig: pass
    class credentials: pass

import os
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.initialized = False
        if not FIREBASE_AVAILABLE:
            logger.warning("firebase-admin is not installed. Push notifications will be disabled.")
            return

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

    async def send_call_notification(
        self,
        token: str,
        caller_name: str,
        call_id: str,
        call_type: str,
        caller_id: str
    ):
        if not self.initialized:
            logger.warning("Attempted to send call notification but Firebase is not initialized.")
            return None

        try:
            # High priority message for calling
            message = messaging.Message(
                notification=messaging.Notification(
                    title="Incoming Call",
                    body=f"{caller_name} is calling you ({call_type})",
                ),
                data={
                    "type": "call",
                    "call_id": str(call_id),
                    "caller_name": caller_name,
                    "call_type": call_type,
                    "caller_id": str(caller_id)
                },
                android=messaging.AndroidConfig(
                    priority='high',
                ),
                apns=messaging.APNSConfig(
                    headers={'apns-priority': '10'},
                ),
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Successfully sent call notification: {response}")
            return response
        except Exception as e:
            logger.error(f"Error sending call notification: {e}")
            return None

notification_service = NotificationService()
