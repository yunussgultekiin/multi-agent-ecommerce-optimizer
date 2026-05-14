import logging
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.logging_config import configure_logging
from app.middleware.auth import JWTAuthMiddleware
from app import limiter
from app.routers.analyze import router as analyze_router
from app.routers.auth import router as auth_router

logger = logging.getLogger(__name__)

_DOWNSTREAM_SERVICES = {
    "auth-service": settings.auth_service_url,
    "task-service": settings.task_service_url,
    "quota-service": settings.quota_service_url,
}

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    logger.info("api_gateway_starting")
    yield
    logger.info("api_gateway_stopping")

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
app.add_middleware(JWTAuthMiddleware)

@app.get("/health")
async def health(request: Request) -> dict:
    dependencies: dict[str, str] = {}

    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, base_url in _DOWNSTREAM_SERVICES.items():
            try:
                response = await client.get(f"{base_url}/health")
            except httpx.HTTPError:
                dependencies[name] = "unreachable"
                continue

            dependencies[name] = "reachable" if response.status_code == 200 else "unreachable"

    return {
        "status": "ok",
        "service": "api-gateway",
        "version": app.version,
        "dependencies": dependencies,
    }

app.include_router(auth_router)
app.include_router(analyze_router)
