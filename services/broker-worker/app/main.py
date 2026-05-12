from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings
from app.consumer import QueueConsumer
from app.database import connect, disconnect
from app.health import router as health_router
from app.logging_config import configure_logging

_consumer = QueueConsumer()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    connect()
    _consumer.start()
    yield
    _consumer.stop()
    disconnect()

app = FastAPI(
    title="Broker Worker",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(health_router)