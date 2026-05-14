from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from app.clients.auth_client import AuthClient, AuthServiceError
from app.config import settings
from app import limiter

router = APIRouter(prefix="/auth", tags=["auth"])
_auth_client = AuthClient()

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit)
async def register(request: Request, body: RegisterRequest):
    try:
        response = await _auth_client.register(body.email, body.password)
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if response.status_code == 409:
        raise HTTPException(status_code=409, detail="Email already registered")
    if response.status_code != 201:
        raise HTTPException(status_code=502, detail="Auth service error")
    return response.json()

@router.post("/login")
@limiter.limit(settings.rate_limit)
async def login(request: Request, body: LoginRequest):
    try:
        response = await _auth_client.login(body.email, body.password)
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Auth service error")
    return response.json()

@router.post("/refresh")
@limiter.limit(settings.rate_limit)
async def refresh(request: Request, body: RefreshRequest):
    try:
        response = await _auth_client.refresh(body.refresh_token)
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if response.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Auth service error")
    return response.json()

@router.get("/me")
@limiter.limit(settings.rate_limit)
async def me(request: Request):
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        response = await _auth_client.me(user_id)
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="User not found")
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Auth service error")
    return response.json()
