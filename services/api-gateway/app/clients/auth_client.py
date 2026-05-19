from app.config import settings
import httpx

class AuthServiceError(Exception):
    pass

class AuthClient:
    def __init__(self) -> None:
        self._base_url = settings.auth_service_url

    async def _request(self, method: str, path: str, **kwargs):
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                return await client.request(method, path, **kwargs)
        except Exception as exc:
            raise AuthServiceError(f"Connection error: {exc}") from exc

    async def register(self, email: str, password: str):
        return await self._request(
            "POST",
            "/auth/register",
            json={"email": email, "password": password},
        )

    async def login(self, email: str, password: str):
        return await self._request(
            "POST",
            "/auth/login",
            json={"email": email, "password": password},
        )

    async def refresh(self, refresh_token: str):
        return await self._request(
            "POST",
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )

    async def me(self, user_id: str):
        return await self._request("GET", f"/internal/users/{user_id}")