from app.database import get_db
from app.repositories import UserRepository
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.security import TokenService
from app.services import (
    AuthService,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
)
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])
_token_service = TokenService()

def _get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        repo=UserRepository(session),
        token_service=_token_service,
        session=session,
    )

@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: RegisterRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        return await service.register(request.email, request.password)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        return await service.login(request.email, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshRequest,
    service: AuthService = Depends(_get_auth_service),
) -> TokenResponse:
    try:
        return await service.refresh(request.refresh_token)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

@router.get("/me", response_model=UserResponse)
async def me(
    http_request: Request,
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    user_id = getattr(http_request.state, "user_id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )

    try:
        return await service.get_current_user(user_id)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
