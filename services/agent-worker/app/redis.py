from app.config import settings
import json
import logging
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)
_redis_client: aioredis.Redis | None = None

async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis_client

async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None

async def report_progress(task_id: str, step: str, status: str, pct: int) -> None:
    try:
        redis = await get_redis()
        payload = {"step": step, "status": status, "pct": pct}
        pipe = redis.pipeline()
        pipe.hset(f"task_progress:{task_id}", mapping=payload)
        pipe.publish(f"progress:{task_id}", json.dumps(payload))
        await pipe.execute()
        logger.debug("Progress reported: task_id=%s step=%s pct=%d", task_id, step, pct)
    except Exception as exc:
        logger.warning(
            "Failed to report progress (Redis unavailable): task_id=%s step=%s error=%s",
            task_id,
            step,
            exc,
        )
