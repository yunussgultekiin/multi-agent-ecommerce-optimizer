from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.redis import connect, disconnect
from app.health import router as health_router
from app.logging_config import configure_logging
from app.router import router as quota_router
from app.security import JWTAuthMiddleware, TokenService

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    await connect()
    yield
    await disconnect()

app = FastAPI(
    title="Quota Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(JWTAuthMiddleware, token_service=TokenService())
app.include_router(health_router)
app.include_router(quota_router)