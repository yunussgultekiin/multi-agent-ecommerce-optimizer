from app.database import get_session
from app.redis import redis_client
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db() -> AsyncSession:
    async with get_session() as session:
        yield session

async def get_redis() -> aioredis.Redis:
    return redis_client
