import logging
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.config import settings
from app.models import TaskRetry

logger = logging.getLogger(__name__)

class MaxRetryExceededError(Exception):
    pass

class RetryHandler:
    def __init__(self, session: Session) -> None:
        self._session = session

    def handle(self, task_id: str, error: str, task_payload: dict, requeue_fn) -> None:
        record = self._get_or_create(task_id)
        record.attempt_count += 1
        record.last_error = error

        if record.attempt_count >= settings.max_retry_count:
            self._session.commit()
            logger.warning(
                "max_retry_exceeded",
                extra={"task_id": task_id, "attempts": record.attempt_count},
            )
            raise MaxRetryExceededError(task_id)

        delay = self._calc_delay(record.attempt_count)
        record.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        self._session.commit()

        logger.info(
            "retry_scheduled",
            extra={
                "task_id": task_id,
                "attempt": record.attempt_count,
                "delay": delay,
            },
        )

        time.sleep(delay)
        requeue_fn(task_id, task_payload)

    def _get_or_create(self, task_id: str) -> TaskRetry:
        record = (
            self._session.query(TaskRetry)
            .filter(TaskRetry.task_id == task_id)
            .first()
        )
        if record is None:
            record = TaskRetry(task_id=task_id)
            self._session.add(record)
            self._session.flush()
        return record

    def _calc_delay(self, attempt: int) -> float:
        return settings.retry_base_delay * (2 ** attempt)