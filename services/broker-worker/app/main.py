from app.config import settings
from app.consumer import QueueConsumer
from app.database import check_db_connectivity, connect, disconnect
from app.logging_config import configure_logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

_consumer = QueueConsumer()

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    connect()
    _consumer.start()
    yield
    _consumer.stop()
    disconnect()

app = FastAPI(title="Broker Worker", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "service": "broker-worker",
        "version": "1.0.0",
        "dependencies": {"postgres": check_db_connectivity()},
    }
