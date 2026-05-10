from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging_config import setup_logging

# Initialize logging immediately
setup_logging()
from app.core.config import settings
from app.api.routes import auth, users, messages, friends, calls
from app.websocket.connection_manager import manager
from app.services.presence_manager import presence_manager
from app.services.chat_manager import ChatManager
from app.services.signaling_manager import SignalingManager
from app.db.session import SessionLocal
from app.core.security import jwt
from jose import JWTError
import asyncio
import json
from app.db.session import engine
from app.admin import setup_admin
from uuid import UUID
from sqlalchemy import update, text
from sqlalchemy.sql import func
from app.models.user import User
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

setup_admin(app, engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(
        f"HTTP {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Duration: {duration:.2f}s"
    )
    return response

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])
app.include_router(friends.router, prefix="/friends", tags=["friends"])
app.include_router(calls.router, prefix="/calls", tags=["calls"])

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": False,
            "message": str(exc.detail),
            "data": None,
            "errors": exc.detail
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "status": False,
            "message": "Validation Error",
            "data": None,
            "errors": exc.errors()
        },
    )

@app.on_event("startup")
async def startup_event():
    # 0. Schema Update (Ensures new columns exist)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE friendships ADD COLUMN IF NOT EXISTS expiry_hours INTEGER DEFAULT 24"))
            await conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_messages_expires_at ON messages (expires_at)"))
            logger.info("Database schema auto-update successful")
    except Exception as e:
        logger.warning(f"Database schema auto-update warning: {e}")

    # Start Redis listener task
    asyncio.create_task(manager.listen_redis())
    
    # Start Message Cleanup background task
    asyncio.create_task(run_cleanup_task())

async def run_cleanup_task():
    """
    Background loop that runs the cleanup service periodically.
    """
    from app.services.cleanup_service import CleanupService
    
    logger.info("Message cleanup background task starting...")
    while True:
        try:
            async with SessionLocal() as db:
                await CleanupService.cleanup_old_messages(db)
            
            # Wait for 1 hour before next cleanup
            await asyncio.sleep(3600) 
        except Exception as e:
            logger.error(f"Error in background cleanup task: {e}")
            await asyncio.sleep(60) # Wait a minute before retrying on error

@app.get("/")
async def root():
    return {"message": "Welcome to SecureChat API"}

@app.websocket("/ws/chat/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    print(f"DEBUG: WebSocket connection attempt received for token: {token[:15]}...")
    await websocket.accept()
    
    # 1. Authenticate
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            print("DEBUG: WebSocket authentication failed: No user_id in payload")
            await websocket.close(code=4001)
            return
    except JWTError as e:
        print(f"DEBUG: WebSocket authentication failed: {str(e)}")
        await websocket.close(code=4001)
        return

    print(f"DEBUG: WebSocket authenticated successfully for user: {user_id}")

    # 2. Connect
    await manager.connect(user_id, websocket)
    await presence_manager.set_online(user_id)
    
    # Update DB status
    async with SessionLocal() as db:
        await db.execute(update(User).where(User.id == UUID(user_id)).values(is_online=True))
        await db.commit()
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            async with SessionLocal() as db:
                if message_data["type"] == "chat_message":
                    await ChatManager.handle_message(db, user_id, message_data)
                
                elif message_data["type"] == "status_update":
                    # Handle delivered/seen status
                    await ChatManager.update_status(
                        db, 
                        UUID(message_data["message_id"]), 
                        message_data["status"]
                    )
                
                elif message_data["type"] in ["offer", "answer", "ice"]:
                    await SignalingManager.relay_signal(user_id, message_data, db=db)
                
                elif message_data["type"] == "typing":
                    # Broadcast typing indicator to receiver
                    receiver_id = message_data.get("receiver_id")
                    await manager.send_personal_message({
                        "type": "typing",
                        "sender_id": user_id,
                        "is_typing": message_data.get("is_typing", True)
                    }, receiver_id)

    except WebSocketDisconnect:
        await manager.disconnect(user_id)
        await presence_manager.set_offline(user_id)
        async with SessionLocal() as db:
            await db.execute(update(User).where(User.id == UUID(user_id)).values(is_online=False, last_seen=func.now()))
            await db.commit()
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(user_id)
        await presence_manager.set_offline(user_id)
        async with SessionLocal() as db:
            await db.execute(update(User).where(User.id == UUID(user_id)).values(is_online=False, last_seen=func.now()))
            await db.commit()
