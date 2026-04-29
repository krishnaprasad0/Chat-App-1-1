from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "SecureChat"
    
    # Auth
    SECRET_KEY: str = "your-secret-key-for-jwt"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    ENCRYPTION_KEY: str = "32-byte-base64-key-here="
    
    # Database
    DATABASE_URL: str
    
    # Redis
    REDIS_URL: str
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()
