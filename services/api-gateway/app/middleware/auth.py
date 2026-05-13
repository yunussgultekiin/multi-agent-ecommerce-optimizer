import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.security import TokenService

logger = logging.getLogger(__name__)

_PUBLIC_PATHS = frozenset({
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/auth/register",
    "/auth/login",
    "/auth/refresh",
})

_token_service = TokenService()

class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid authorization header"},
                status_code=401,
            )

        token = authorization[len("Bearer "):]

        try:
            user_id = _token_service.get_user_id(token)
        except ValueError:
            return JSONResponse(
                {"detail": "Invalid or expired token"},
                status_code=401,
            )

        request.state.user_id = user_id
        request.state.token = token
        return await call_next(request)