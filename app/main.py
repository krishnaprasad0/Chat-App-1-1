from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth, users, messages
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

app = FastAPI(title=settings.PROJECT_NAME)

setup_admin(app, engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(messages.router, prefix="/messages", tags=["messages"])

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
    # Start Redis listener task
    asyncio.create_task(manager.listen_redis())

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
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            async with SessionLocal() as db:
                if message_data["type"] == "chat_message":
                    await ChatManager.handle_message(db, user_id, message_data)
                
                elif message_data["type"] in ["offer", "answer", "ice"]:
                    await SignalingManager.relay_signal(user_id, message_data)
                
                elif message_data["type"] == "typing":
                    # Broadcast typing indicator to receiver
                    receiver_id = message_data.get("receiver_id")
                    await manager.send_personal_message({
                        "type": "typing",
                        "sender_id": user_id,
                        "is_typing": message_data.get("is_typing", True)
                    }, receiver_id)

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await presence_manager.set_offline(user_id)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        manager.disconnect(user_id)
        await presence_manager.set_offline(user_id)
