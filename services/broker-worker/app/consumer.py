import json
import logging
import threading
import redis
from app.agent_client import AgentClient, AgentClientError
from app.config import settings
from app.database import get_session
from app.retry_handler import MaxRetryExceededError, RetryHandler
from app.task_service_client import TaskServiceClient

logger = logging.getLogger(__name__)

class QueueConsumer:
    def __init__(self) -> None:
        self._redis = redis.from_url(settings.redis_url, decode_responses=True)
        self._agent_client = AgentClient()
        self._task_service_client = TaskServiceClient()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True, name="queue-consumer")
        self._thread.start()
        logger.info("queue_consumer_started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        self._redis.close()
        logger.info("queue_consumer_stopped")

    def _run(self) -> None:
        logger.info("consumer_loop_started", extra={"queue": settings.task_queue_name})

        while not self._stop_event.is_set():
            try:
                result = self._redis.blpop(settings.task_queue_name, timeout=2)

                if result is None:
                    continue

                _, raw = result
                task = json.loads(raw)
                task_id = task["task_id"]
                payload = task.get("payload", {})

                logger.info("task_received", extra={"task_id": task_id})
                self._process(task_id, payload)

            except Exception as exc:
                logger.error("consumer_loop_error", extra={"error": str(exc)})

    def _process(self, task_id: str, payload: dict) -> None:
        try:
            self._agent_client.run(task_id, payload)
            self._notify_running(task_id)
        except AgentClientError as exc:
            threading.Thread(
                target=self._handle_retry,
                args=(task_id, str(exc), payload),
                daemon=True,
                name=f"retry-{task_id}",
            ).start()

    def _handle_retry(self, task_id: str, error: str, payload: dict) -> None:
        session = get_session()
        try:
            retry_handler = RetryHandler(session=session)
            retry_handler.handle(
                task_id=task_id,
                error=error,
                task_payload=payload,
                requeue_fn=self._requeue,
            )
        except MaxRetryExceededError:
            self._notify_failed(task_id)
        finally:
            session.close()

    def _requeue(self, task_id: str, payload: dict) -> None:
        task = json.dumps({"task_id": task_id, "payload": payload})
        self._redis.rpush(settings.task_queue_name, task)
        logger.info("task_requeued", extra={"task_id": task_id})

    def _notify_running(self, task_id: str) -> None:
        self._task_service_client.update_status(task_id, "running")
        logger.info("task_running_notified", extra={"task_id": task_id})

    def _notify_failed(self, task_id: str) -> None:
        self._task_service_client.update_status(task_id, "failed")
        logger.error("task_failed_notified", extra={"task_id": task_id})