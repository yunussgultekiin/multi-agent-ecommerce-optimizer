from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis
from app.core.redis import redis_client
from app.core.database import get_session

async def get_db() -> AsyncSession:
    async with get_session() as session:
        yield session

async def get_redis() -> aioredis.Redis:
    return redis_client
