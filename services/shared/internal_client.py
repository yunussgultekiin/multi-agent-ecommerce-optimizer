import asyncio
import httpx
import jwt as pyjwt
import threading
import time
from typing import Optional

_REFRESH_BUFFER = 30
_TOKEN_TTL = 300


class SyncInternalTokenProvider:
    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._cached: Optional[str] = None
        self._expiry: float = 0.0
        self._lock = threading.Lock()

    def get_token(self) -> str:
        with self._lock:
            now = time.time()
            if self._cached and now < self._expiry - _REFRESH_BUFFER:
                return self._cached
            exp = now + _TOKEN_TTL
            self._cached = pyjwt.encode(
                {"iss": "internal-service", "exp": int(exp)},
                self._secret,
                algorithm=self._algorithm,
            )
            self._expiry = exp
            return self._cached

    def attach_to_headers(self, headers: dict) -> dict:
        return {**headers, "Authorization": f"Bearer {self.get_token()}"}


class InternalTokenProvider:
    def __init__(self, secret: str, algorithm: str = "HS256") -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._cached: Optional[str] = None
        self._expiry: float = 0.0
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        async with self._lock:
            now = time.time()
            if self._cached and now < self._expiry - _REFRESH_BUFFER:
                return self._cached
            exp = now + _TOKEN_TTL
            self._cached = pyjwt.encode(
                {"iss": "internal-service", "exp": int(exp)},
                self._secret,
                algorithm=self._algorithm,
            )
            self._expiry = exp
            return self._cached

    async def attach_header(self, headers: dict) -> dict:
        token = await self.get_token()
        return {**headers, "Authorization": f"Bearer {token}"}


class InternalHttpClient:
    def __init__(self, base_url: str, secret: str, algorithm: str = "HS256") -> None:
        self._base_url = base_url
        self._provider = InternalTokenProvider(secret, algorithm)

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = await self._provider.attach_header(kwargs.pop("headers", {}))
        async with httpx.AsyncClient(base_url=self._base_url) as client:
            return await client.request(method, path, headers=headers, **kwargs)

    async def get(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("POST", path, **kwargs)

    async def patch(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", path, **kwargs)

    async def delete(self, path: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", path, **kwargs)
