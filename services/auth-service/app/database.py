from app.config import settings
from google.cloud.sql.connector import AsyncConnector, IPTypes
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

def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        echo=False,
    )

async def build_engine_with_connector(connector: AsyncConnector) -> AsyncEngine:
    ip_type = IPTypes.PRIVATE if settings.db_ip_type == "PRIVATE" else IPTypes.PUBLIC

    async def _getconn():
        return await connector.connect_async(
            settings.cloud_sql_instance,
            "asyncpg",
            user=settings.db_user,
            password=settings.db_pass,
            db=settings.db_name,
            ip_type=ip_type,
        )

    return create_async_engine(
        "postgresql+asyncpg://",
        async_creator=_getconn,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
    )

def init_engine(engine: AsyncEngine) -> None:
    global _engine, _session_maker
    _engine = engine
    _session_maker = async_sessionmaker(engine, expire_on_commit=False)

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
