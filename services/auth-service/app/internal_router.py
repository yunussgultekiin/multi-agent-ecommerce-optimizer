from app.database import get_db
from app.repositories import UserRepository
from app.schemas import UserResponse
from app.security import TokenService
from app.services import AuthService, InvalidCredentialsError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/internal", tags=["internal"])
_token_service = TokenService()

def _get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(
        repo=UserRepository(session),
        token_service=_token_service,
        session=session,
    )

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    service: AuthService = Depends(_get_auth_service),
) -> UserResponse:
    try:
        return await service.get_current_user(user_id)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
