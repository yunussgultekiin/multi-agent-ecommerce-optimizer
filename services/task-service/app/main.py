import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.health import router as health_router
from app.database import connect, disconnect

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
app.include_router(health_router)
