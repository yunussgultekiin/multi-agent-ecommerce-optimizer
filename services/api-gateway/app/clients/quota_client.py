from app.config import settings
from shared.internal_client import InternalHttpClient

class QuotaServiceError(Exception):
    pass

class QuotaClient:
    def __init__(self) -> None:
        self._client = InternalHttpClient(
            base_url=settings.quota_service_url,
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def _request(self, method: str, path: str, **kwargs):
        try:
            return await self._client.request(method, path, **kwargs)
        except Exception as exc:
            raise QuotaServiceError(f"Connection error: {exc}") from exc

    async def check(self, user_id: str):
        return await self._request("GET", f"/quota/{user_id}")

    async def consume(self, user_id: str):
        return await self._request("POST", f"/quota/{user_id}/consume")
