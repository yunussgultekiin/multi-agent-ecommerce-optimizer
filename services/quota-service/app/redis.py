from app.config import settings
import logging
import redis.asyncio as aioredis
from typing import AsyncGenerator

logger = logging.getLogger(__name__)
_redis: aioredis.Redis | None = None

async def connect() -> None:
    global _redis
    _redis = aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )
    await _redis.ping()
    logger.info("redis_connected", extra={"url": settings.redis_url})

async def disconnect() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        logger.info("redis_disconnected")

def get_client() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised")
    return _redis

async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    yield get_client()

async def check_redis_connectivity() -> str:
    if _redis is None:
        return "error"
    try:
        await _redis.ping()
        return "ok"
    except Exception:
        return "error"
