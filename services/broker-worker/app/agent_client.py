import logging
import httpx
from app.config import settings
from shared.oidc_client import SyncInternalTokenProvider

logger = logging.getLogger(__name__)
class AgentClientError(Exception): pass

class AgentClient:
    def __init__(self) -> None:
        self._base_url = settings.agent_worker_url
        self._timeout = 10.0
        self._auth = SyncInternalTokenProvider(
            secret=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

    def run(self, task_id: str, payload: dict, agent_type: str = "rival") -> None:
        headers = self._auth.attach_to_headers({})
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout) as client:
                response = client.post(
                    f"/run/{agent_type}",
                    json={"task_id": task_id, "payload": payload},
                    headers=headers,
                )
            if response.status_code != 202:
                raise AgentClientError(f"Unexpected status code: {response.status_code}")
            logger.info("agent_notified", extra={"task_id": task_id, "agent_type": agent_type})
        except httpx.RequestError as exc:
            raise AgentClientError(f"Connection error: {exc}") from exc
