import logging
import uuid
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import create_user, get_user_by_email, get_user_by_id
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(request: RegisterRequest, session: AsyncSession = Depends(get_db)):
    if await get_user_by_email(session, request.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = await create_user(session, request.email, hash_password(request.password))
    await session.commit()
    await session.refresh(user)

    logger.info("user_registered", extra={"user_id": str(user.id)})
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(session, request.email)

    if user is None:
        bcrypt.checkpw(b"dummy", bcrypt.hashpw(b"dummy", bcrypt.gensalt()))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account inactive")

    logger.info("user_logged_in", extra={"user_id": str(user.id)})
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(request: RefreshRequest, session: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token, expected_type="refresh")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    user = await get_user_by_id(session, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )

@router.get("/me", response_model=UserResponse)
async def me(http_request: Request, session: AsyncSession = Depends(get_db)):
    user_id_str = getattr(http_request.state, "user_id", None)
    if user_id_str is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = await get_user_by_id(session, uuid.UUID(user_id_str))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return UserResponse(id=user.id, email=user.email, is_active=user.is_active)
