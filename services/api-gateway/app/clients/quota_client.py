import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class QuotaServiceError(Exception):
    pass

class QuotaClient:
    def __init__(self) -> None:
        self._base_url = settings.quota_service_url

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                return await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise QuotaServiceError(f"Connection error: {exc}") from exc

    async def check(self, user_id: str) -> httpx.Response:
        return await self.request("GET", f"/quota/{user_id}")

    async def consume(self, user_id: str) -> httpx.Response:
        return await self.request("POST", f"/quota/{user_id}/consume")