import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class TaskServiceError(Exception):
    pass

class TaskClient:
    def __init__(self) -> None:
        self._base_url = settings.task_service_url

    async def request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            async with httpx.AsyncClient(base_url=self._base_url) as client:
                return await client.request(method, path, **kwargs)
        except httpx.RequestError as exc:
            raise TaskServiceError(f"Connection error: {exc}") from exc

    async def create_task(self, user_id: str, payload: dict) -> httpx.Response:
        return await self.request(
            "POST", "/tasks",
            json={"user_id": user_id, "payload": payload},
        )

    async def get_task(self, task_id: str) -> httpx.Response:
        return await self.request("GET", f"/tasks/{task_id}")

    async def get_result(self, task_id: str) -> httpx.Response:
        return await self.request("GET", f"/tasks/{task_id}/result")

    async def get_history(self, user_id: str) -> httpx.Response:
        return await self.request("GET", f"/tasks", params={"user_id": user_id})