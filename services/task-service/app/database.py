import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase

_DATABASE_URL: str = os.getenv("DATABASE_URL", "")
engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker | None = None

async def connect() -> None:
    global engine, async_session_maker
    if not _DATABASE_URL:
        return
    engine = create_async_engine(
        _DATABASE_URL,
        pool_pre_ping = True,
        pool_size = 5,
        max_overflow = 15,
        pool_timeout = 15,
        echo=False
    )
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def disconnect() -> None:
    if engine:
        await engine.dispose()

@asynccontextmanager
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
