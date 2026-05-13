import json
import logging
from app.redis_client import get_redis

logger = logging.getLogger(__name__)

async def report_progress(task_id: str, step: str, status: str, pct: int) -> None:
    redis = await get_redis()
    payload = {"step": step, "status": status, "pct": pct}
    pipe = redis.pipeline()
    pipe.hset(f"task_progress:{task_id}", mapping=payload)
    pipe.publish(f"progress:{task_id}", json.dumps(payload))
    await pipe.execute()
    logger.debug("Progress reported: task_id=%s step=%s pct=%d", task_id, step, pct)
