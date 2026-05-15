from app.config import settings
import bcrypt
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import Literal
import uuid

logger = logging.getLogger(__name__)
TokenType = Literal["access", "refresh"]
_DUMMY_HASH = bcrypt.hashpw(
    b"dummy_timing_placeholder", bcrypt.gensalt(rounds=12)
).decode()

_JWT_SKIP_PATHS = frozenset(
    {
        "/auth/register",
        "/auth/login",
        "/auth/refresh",
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    }
)

_JWT_SKIP_PREFIXES = frozenset({"/internal/"})

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def dummy_verify() -> None:
    bcrypt.checkpw(b"x", _DUMMY_HASH.encode())

class TokenService:
    def __init__(self) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm
        self._access_expire_minutes = settings.access_token_expire_minutes
        self._refresh_expire_days = settings.refresh_token_expire_days

    def create_access_token(self, user_id: uuid.UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=self._access_expire_minutes),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def create_refresh_token(self, user_id: uuid.UUID) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=self._refresh_expire_days),
        }
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode_token(self, token: str, expected_type: TokenType | None = None) -> dict:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except InvalidTokenError as exc:
            raise ValueError(str(exc)) from exc

        if expected_type is not None and payload.get("type") != expected_type:
            raise ValueError(
                f"Expected token type '{expected_type}', got '{payload.get('type')}'"
            )

        return payload

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_service: TokenService, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self._token_service = token_service

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in _JWT_SKIP_PATHS or any(
            path.startswith(p) for p in _JWT_SKIP_PREFIXES
        ):
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid authorization header"}, status_code=401
            )

        try:
            payload = self._token_service.decode_token(
                authorization[len("Bearer ") :], expected_type="access"
            )
        except ValueError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        request.state.user_id = payload["sub"]
        return await call_next(request)
