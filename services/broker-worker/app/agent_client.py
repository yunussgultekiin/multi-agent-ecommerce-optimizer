import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class AgentClientError(Exception):
    pass


class AgentClient:
    def __init__(self) -> None:
        self._base_url = settings.agent_worker_url
        self._timeout = 10.0

    def run(self, task_id: str, payload: dict) -> None:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(
                    "/run",
                    json={"task_id": task_id, "payload": payload},
                )

            if response.status_code != 202:
                raise AgentClientError(
                    f"Unexpected status code: {response.status_code}"
                )

            logger.info(
                "agent_notified",
                extra={"task_id": task_id},
            )

        except httpx.RequestError as exc:
            raise AgentClientError(f"Connection error: {exc}") from exc