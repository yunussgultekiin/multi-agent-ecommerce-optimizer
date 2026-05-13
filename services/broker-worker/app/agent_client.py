import logging
import httpx
from app.config import settings
from app.oidc_sync import SyncOidcTokenProvider

logger = logging.getLogger(__name__)
class AgentClientError(Exception): pass

class AgentClient:
    def __init__(self) -> None:
        self._base_url = settings.agent_worker_url
        self._timeout = 10.0
        self._oidc = SyncOidcTokenProvider(audience=settings.agent_worker_url)

    def run(self, task_id: str, payload: dict, agent_type: str = "rival") -> None:
        headers = self._oidc.attach_to_headers({})
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
