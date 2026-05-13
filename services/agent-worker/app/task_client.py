import logging
from shared.oidc_client import OidcHttpClient
from app.config import settings

logger = logging.getLogger(__name__)

class TaskServiceClient:
    def __init__(self) -> None:
        self._client = OidcHttpClient(base_url=settings.task_service_url)

    async def update_status(self, task_id: str, status: str, error_message: str | None = None) -> None:
        body: dict = {"status": status}
        if error_message:
            body["error_message"] = error_message
        try:
            response = await self._client.request(
                "PATCH",
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
