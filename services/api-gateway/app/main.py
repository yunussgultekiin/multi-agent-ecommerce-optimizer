import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.health import router as health_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    logger.info("api-gateway starting up")
    yield
    logger.info("api-gateway shutting down")


app = FastAPI(title="API Gateway", version="0.1.0", lifespan=lifespan)
app.include_router(health_router)
