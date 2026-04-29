from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    username: str

class TokenPayload(BaseModel):
    sub: str = None
    exp: int = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str
