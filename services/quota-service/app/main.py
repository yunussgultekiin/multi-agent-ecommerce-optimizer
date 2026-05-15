from app.config import settings
from app.logging_config import configure_logging
from app.redis import check_redis_connectivity, connect, disconnect
from app.router import router as quota_router
from app.security import JWTAuthMiddleware, TokenService
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    await connect()
    yield
    await disconnect()

app = FastAPI(title="Quota Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(JWTAuthMiddleware, token_service=TokenService())
app.include_router(quota_router)

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "quota-service",
        "version": "1.0.0",
        "dependencies": {"redis": await check_redis_connectivity()},
    }
