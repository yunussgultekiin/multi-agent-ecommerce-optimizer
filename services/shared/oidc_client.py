import asyncio
import logging
import time
from typing import Optional
import httpx
import jwt as pyjwt
import google.auth.transport.requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)
_OIDC_REFRESH_BUFFER = 30

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
            request = google.auth.transport.requests.Request()
            token = id_token.fetch_id_token(request, self._audience)
            payload = pyjwt.decode(token, options={"verify_signature": False})
            return token, float(payload.get("exp", time.time() + 3600))
        except Exception:
            logger.debug("OIDC token fetch skipped (not running on GCP)")
            return None, 0.0

    async def attach_oidc_header(self, headers: dict) -> dict:
        token = await self.get_token()
        if token is None:
            return headers
        return {**headers, "Authorization": f"Bearer {token}"}

class OidcHttpClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._provider = OidcTokenProvider(audience=base_url)

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        headers = await self._provider.attach_oidc_header(kwargs.pop("headers", {}))
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
