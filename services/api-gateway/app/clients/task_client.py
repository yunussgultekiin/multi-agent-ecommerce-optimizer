from shared.oidc_client import InternalHttpClient
from app.config import settings

class TaskServiceError(Exception): pass

class TaskClient:
    def __init__(self) -> None:
        self._client = InternalHttpClient(
            base_url=settings.task_service_url,
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def _request(self, method: str, path: str, **kwargs):
        try:
            return await self._client.request(method, path, **kwargs)
        except Exception as exc:
            raise TaskServiceError(f"Connection error: {exc}") from exc

    async def create_task(self, user_id: str, payload: dict):
        return await self._request(
            "POST",
            "/tasks",
            json={"user_id": user_id, "payload": payload},
        )

    async def get_task(self, task_id: str, user_id: str):
        return await self._request(
            "GET",
            f"/tasks/{task_id}",
            params={"user_id": user_id},
        )

    async def get_result(self, task_id: str, user_id: str):
        return await self._request(
            "GET",
            f"/tasks/{task_id}/result",
            params={"user_id": user_id},
        )

    async def get_history(self, user_id: str):
        return await self._request("GET", "/tasks", params={"user_id": user_id})
