import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

_DATABASE_URL: str = os.getenv("DATABASE_URL", "")
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker | None = None


async def connect() -> None:
    global engine, async_session_maker
    if not _DATABASE_URL:
        return
    engine = create_async_engine(_DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def disconnect() -> None:
    if engine:
        await engine.dispose()


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if async_session_maker is None:
        raise RuntimeError("Database not initialised")
    async with async_session_maker() as session:
        yield session


async def check_database_connectivity() -> str:
    if engine is None:
        return "error"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"
