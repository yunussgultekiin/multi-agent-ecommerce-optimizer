import logging
import jwt
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings

logger = logging.getLogger(__name__)

_PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
})

class TokenService:
    def __init__(self) -> None:
        self._secret = settings.jwt_secret_key
        self._algorithm = settings.jwt_algorithm

    def decode_token(self, token: str) -> dict:
        try:
            return jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
            )
        except InvalidTokenError as exc:
            raise ValueError(str(exc)) from exc

class JWTAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token_service: TokenService, **kwargs) -> None:
        super().__init__(app, **kwargs)
        self._token_service = token_service

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid authorization header"},
                status_code=401,
            )

        try:
            self._token_service.decode_token(authorization[len("Bearer "):])
        except ValueError:
            return JSONResponse(
                {"detail": "Invalid or expired token"},
                status_code=401,
            )

        return await call_next(request)