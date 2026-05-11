import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import bcrypt
import httpx
import jwt
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.config import settings

logger = logging.getLogger(__name__)
TokenType = Literal["access", "refresh"]

_PUBLIC_PATHS = frozenset(
    {"/auth/register", "/auth/login", "/auth/refresh", "/health", "/docs", "/openapi.json", "/redoc"}
)

_OIDC_REFRESH_BUFFER = 30

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

def create_access_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def create_refresh_token(user_id: uuid.UUID) -> str:
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

def decode_token(token: str, expected_type: TokenType | None = None) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise ValueError(str(exc)) from exc

    if expected_type is not None and payload.get("type") != expected_type:
        raise ValueError(f"Expected token type '{expected_type}', got '{payload.get('type')}'")
    return payload

class JWTAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        authorization = request.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse({"detail": "Missing or invalid authorization header"}, status_code=401)

        try:
            payload = decode_token(authorization[len("Bearer "):], expected_type="access")
        except ValueError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        request.state.user_id = payload["sub"]
        return await call_next(request)

class OidcTokenProvider:
    def __init__(self, audience: str) -> None:
        self._audience = audience
        self._cached_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> Optional[str]:
        async with self._lock:
            now = time.time()
            if self._cached_token is not None and now < self._token_expiry - _OIDC_REFRESH_BUFFER:
                return self._cached_token
            token, exp = await asyncio.get_event_loop().run_in_executor(None, self._fetch_token_sync)
            self._cached_token = token
            self._token_expiry = exp
            return token

    def _fetch_token_sync(self) -> tuple[Optional[str], float]:
        try:
            import google.auth.transport.requests
            from google.oauth2 import id_token
            import jwt as pyjwt

            request = google.auth.transport.requests.Request()
            token = id_token.fetch_id_token(request, self._audience)
            payload = pyjwt.decode(token, options={"verify_signature": False})
            return token, float(payload.get("exp", time.time() + 3600))
        except Exception:
            logger.debug("OIDC token fetch skipped (not running on GCP)")
            return None, 0.0

    async def attach_to_headers(self, headers: dict) -> dict:
        token = await self.get_token()
        if token is None:
            return headers
        return {**headers, "Authorization": f"Bearer {token}"}

class OidcHttpClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._provider = OidcTokenProvider(audience=base_url)

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = await self._provider.attach_to_headers(kwargs.pop("headers", {}))
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            return await client.request(method, path, headers=headers, **kwargs)

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
