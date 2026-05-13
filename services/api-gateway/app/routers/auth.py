import logging
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from app.clients.auth_client import AuthClient, AuthServiceError

logger = logging.getLogger(__name__)

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
async def register(request: RegisterRequest):
    try:
        response = await _auth_client.register(request.email, request.password)
        if response.status_code == 409:
            raise HTTPException(status_code=409, detail="Email already registered")
        if response.status_code != 201:
            raise HTTPException(status_code=502, detail="Auth service error")
        return response.json()
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

@router.post("/login")
async def login(request: LoginRequest):
    try:
        response = await _auth_client.login(request.email, request.password)
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Auth service error")
        return response.json()
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

@router.post("/refresh")
async def refresh(request: RefreshRequest):
    try:
        response = await _auth_client.refresh(request.refresh_token)
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Auth service error")
        return response.json()
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")

@router.get("/me")
async def me(http_request: Request):
    token = getattr(http_request.state, "token", None)
    if token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        response = await _auth_client.me(token)
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Not authenticated")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Auth service error")
        return response.json()
    except AuthServiceError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")