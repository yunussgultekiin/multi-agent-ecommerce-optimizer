import logging
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

QUOTA_KEY_PREFIX = "quota"

def _key(user_id: str) -> str:
    return f"{QUOTA_KEY_PREFIX}:{user_id}"

class QuotaRepository:
    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def get(self, user_id: str) -> int:
        value = await self._redis.get(_key(user_id))
        return int(value) if value is not None else 0

    async def increment(self, user_id: str) -> int:
        return await self._redis.incr(_key(user_id))

    async def set_ttl_if_new(self, user_id: str) -> None:
        key = _key(user_id)
        ttl = await self._redis.ttl(key)
        if ttl == -1:
            await self._redis.expire(key, settings.quota_ttl_seconds)

    async def reset(self, user_id: str) -> None:
        await self._redis.delete(_key(user_id))

    async def get_ttl(self, user_id: str) -> int:
        return await self._redis.ttl(_key(user_id))