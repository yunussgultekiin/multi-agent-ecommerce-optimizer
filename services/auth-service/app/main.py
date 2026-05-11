from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.database import connect, disconnect
from app.health import router as health_router
from app.logging_config import configure_logging
from app.router import router as auth_router
from app.security import JWTAuthMiddleware

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    await connect()
    yield
    await disconnect()

app = FastAPI(title="Auth Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(JWTAuthMiddleware)
app.include_router(health_router)
app.include_router(auth_router)
