from app.config import settings
from app.database import (
    check_database_connectivity,
    disconnect,
    _build_engine,
    build_engine_with_connector,
    init_engine,
)
from app.internal_router import router as internal_router
from app.logging_config import configure_logging
from app.router import router as auth_router
from app.security import JWTAuthMiddleware, TokenService
from contextlib import asynccontextmanager
from fastapi import FastAPI
from google.cloud.sql.connector import AsyncConnector

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    connector = None
    if settings.cloud_sql_instance:
        connector = AsyncConnector()
        engine = await build_engine_with_connector(connector)
    else:
        engine = _build_engine()
    init_engine(engine)
    yield
    await disconnect()
    if connector:
        await connector.close()

app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(JWTAuthMiddleware, token_service=TokenService())
app.include_router(internal_router)
app.include_router(auth_router)

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "auth-service",
        "version": "1.0.0",
        "dependencies": {"postgres": await check_database_connectivity()},
    }
