import os
import redis.asyncio as aioredis

_REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_client: aioredis.Redis | None = None


async def connect() -> None:
    global _client
    _client = aioredis.from_url(_REDIS_URL, decode_responses=True)


async def disconnect() -> None:
    if _client:
        await _client.aclose()


async def check_redis_connectivity() -> str:
    if _client is None:
        return "error"
    try:
        await _client.ping()
        return "ok"
    except Exception:
        return "error"
