from app.config import settings
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

_engine = None
_session_maker = None

def connect() -> None:
    global _engine, _session_maker
    _engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _session_maker = sessionmaker(_engine, expire_on_commit=False)
    logger.info("database_connected")

def disconnect() -> None:
    global _engine
    if _engine:
        _engine.dispose()
        logger.info("database_disconnected")

def get_session() -> Session:
    if _session_maker is None:
        raise RuntimeError("Database not initialised")
    return _session_maker()

def check_db_connectivity() -> str:
    if _engine is None:
        return "error"
    try:
        with _engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"
