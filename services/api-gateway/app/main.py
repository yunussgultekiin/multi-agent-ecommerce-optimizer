import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.health import router as health_router
from app.logging_config import configure_logging
from app.middleware.auth import JWTAuthMiddleware
from app.middleware.quota import QuotaCheckMiddleware
from app.routers.auth import router as auth_router
from app.routers.analyze import router as analyze_router

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("api-gateway starting up")
    yield
    logger.info("api-gateway shutting down")

app = FastAPI(title="API Gateway", version="1.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(QuotaCheckMiddleware)
app.add_middleware(JWTAuthMiddleware)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(analyze_router)