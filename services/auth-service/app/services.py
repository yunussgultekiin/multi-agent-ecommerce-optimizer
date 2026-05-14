import logging
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import User
from app.repositories import UserRepository
from app.schemas import TokenResponse, UserResponse
from app.security import TokenService, dummy_verify, hash_password, verify_password

logger = logging.getLogger(__name__)


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass

class AuthService:
    def __init__(
        self,
        repo: UserRepository,
        token_service: TokenService,
        session: AsyncSession,
    ) -> None:
        self._repo = repo
        self._token_service = token_service
        self._session = session

    async def register(self, email: str, password: str) -> TokenResponse:
        if await self._repo.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(email)

        user = await self._repo.create(email, hash_password(password))
        await self._session.commit()

        logger.info("user_registered", extra={"user_id": str(user.id)})
        return self._build_token_response(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self._repo.get_by_email(email)

        if user is None:
            dummy_verify()
            raise InvalidCredentialsError("Invalid credentials")

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid credentials")

        if not user.is_active:
            raise InvalidCredentialsError("Account inactive")

        logger.info("user_logged_in", extra={"user_id": str(user.id)})
        return self._build_token_response(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = self._token_service.decode_token(refresh_token, expected_type="refresh")
        except ValueError as exc:
            raise InvalidCredentialsError("Invalid or expired refresh token") from exc

        user = await self._repo.get_by_id(uuid.UUID(payload["sub"]))
        if user is None or not user.is_active:
            raise InvalidCredentialsError("User not found or inactive")

        return self._build_token_response(user)

    async def get_current_user(self, user_id: str) -> UserResponse:
        user = await self._repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            raise InvalidCredentialsError("User not found")

        return UserResponse(id=user.id, email=user.email, is_active=user.is_active)

    def _build_token_response(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=self._token_service.create_access_token(user.id),
            refresh_token=self._token_service.create_refresh_token(user.id),
        )
