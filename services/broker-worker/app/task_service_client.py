import logging
import httpx
from app.config import settings
from shared.oidc_client import SyncOidcTokenProvider

logger = logging.getLogger(__name__)

class TaskServiceClient:
    def __init__(self) -> None:
        self._base_url = settings.task_service_url
        self._timeout = 10.0
        self._oidc = SyncOidcTokenProvider(audience=settings.task_service_url)

    def update_status(self, task_id: str, status: str) -> None:
        headers = self._oidc.attach_to_headers({})
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.patch(
                    f"/tasks/{task_id}/status",
                    json={"status": status},
                    headers=headers,
                )
            if response.status_code not in (200, 204):
                logger.warning(
                    "task_status_update_unexpected_response",
                    extra={"task_id": task_id, "status": status, "code": response.status_code},
                )
        except httpx.RequestError as exc:
            logger.error(
                "task_service_connection_error",
                extra={"task_id": task_id, "error": str(exc)},
            )
