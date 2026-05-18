from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator

class Base(DeclarativeBase):
    pass

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker | None = None

async def connect() -> None:
    global _engine, _session_maker
    _engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=False,
    )
    _session_maker = async_sessionmaker(_engine, expire_on_commit=False)

def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("Database not initialised")
    return _engine

async def disconnect() -> None:
    if _engine:
        await _engine.dispose()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if _session_maker is None:
        raise RuntimeError("Database not initialised")
    async with _session_maker() as session:
        yield session

async def check_database_connectivity() -> str:
    if _engine is None:
        return "error"
    try:
        async with _engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"
