from app.config import settings
import logging
from shared.internal_client import InternalHttpClient

logger = logging.getLogger(__name__)

class TaskServiceClient:
    def __init__(self) -> None:
        self._client = InternalHttpClient(
            base_url=settings.task_service_url,
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    async def save_result(self, task_id: str, result: dict) -> None:
        try:
            response = await self._client.post(
                f"/tasks/{task_id}/result",
                json={"result": result},
            )
            if response.status_code not in (200, 201):
                logger.warning(
                    "Unexpected save_result response: task_id=%s code=%d",
                    task_id,
                    response.status_code,
                )
        except Exception as exc:
            logger.error("Failed to save result: task_id=%s error=%s", task_id, exc)

    async def update_status(
        self, task_id: str, status: str, error_message: str | None = None
    ) -> None:
        body: dict = {"status": status}
        if error_message:
            body["error_message"] = error_message
        try:
            response = await self._client.patch(
                f"/tasks/{task_id}/status",
                json=body,
            )
            if response.status_code not in (200, 204):
                logger.warning(
                    "Unexpected task status update response: task_id=%s status=%s code=%d",
                    task_id,
                    status,
                    response.status_code,
                )
        except Exception as exc:
            logger.error(
                "Failed to update task status: task_id=%s status=%s error=%s",
                task_id,
                status,
                exc,
            )
