import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class AuthServiceError(Exception):
    pass

class AuthClient:
    def __init__(self) -> None:
        self._base_url = settings.auth_service_url

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                return await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise AuthServiceError(f"Connection error: {exc}") from exc

    async def register(self, email: str, password: str) -> httpx.Response:
        return await self.request(
            "POST", "/auth/register",
            json={"email": email, "password": password},
        )

    async def login(self, email: str, password: str) -> httpx.Response:
        return await self.request(
            "POST", "/auth/login",
            json={"email": email, "password": password},
        )

    async def refresh(self, refresh_token: str) -> httpx.Response:
        return await self.request(
            "POST", "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    async def me(self, token: str) -> httpx.Response:
        return await self.request(
            "GET", "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )