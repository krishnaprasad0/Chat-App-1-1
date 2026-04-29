from cryptography.fernet import Fernet
from app.core.config import settings

class MessageEncryptor:
    def __init__(self):
        self.fernet = Fernet(settings.ENCRYPTION_KEY.encode())

    def encrypt(self, text: str) -> str:
        if not text:
            return text
        return self.fernet.encrypt(text.encode()).decode()

    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return encrypted_text
        try:
            return self.fernet.decrypt(encrypted_text.encode()).decode()
        except Exception:
            # Fallback if decryption fails (e.g. legacy data)
            return encrypted_text

encryptor = MessageEncryptor()
