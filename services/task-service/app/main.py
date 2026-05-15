from app.database import check_database_connectivity, connect, disconnect
from app.security import JWTAuthMiddleware, TokenService
from app.tasks_router import router as tasks_router
from contextlib import asynccontextmanager
from fastapi import FastAPI
import logging

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    logger.info("task-service starting up")
    await connect()
    yield
    await disconnect()
    logger.info("task-service shutting down")

app = FastAPI(title="Task Service", version="0.1.0", lifespan=lifespan)
app.add_middleware(JWTAuthMiddleware, token_service=TokenService())
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "task-service",
        "version": "0.1.0",
        "dependencies": {"postgres": await check_database_connectivity()},
    }
