import logging
from typing import Any, Awaitable, Callable
from app.redis import get_redis, report_progress

logger = logging.getLogger(__name__)

async def _is_cancelled(task_id: str) -> bool:
    redis = await get_redis()
    exists = await redis.exists(f"cancelled:{task_id}")
    if exists:
        logger.info("Cancellation signal detected: task_id=%s", task_id)
    return bool(exists)

class NodeRunner:
    def __init__(self, step_name: str, completion_pct: int) -> None:
        self._step_name = step_name
        self._completion_pct = completion_pct

    def wrap(
        self,
        node_fn: Callable[[Any], Awaitable[Any]],
    ) -> Callable[[Any], Awaitable[Any]]:
        step_name = self._step_name
        completion_pct = self._completion_pct

        async def execute(state: dict) -> dict:
            task_id = state["task_id"]
            if await _is_cancelled(task_id):
                logger.info("Node skipped due to cancellation: task_id=%s step=%s", task_id, step_name)
                return {**state, "cancelled": True, "status": "cancelled"}
            await report_progress(task_id, step_name, "running", completion_pct)
            updated_state = await node_fn(state)
            if not updated_state.get("cancelled"):
                await report_progress(task_id, step_name, "completed", completion_pct)
            return updated_state

        return execute
