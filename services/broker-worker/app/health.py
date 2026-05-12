import asyncio
import logging
import os

import redis.asyncio as aioredis
from aiohttp import web

logger = logging.getLogger(__name__)


async def health_handler(request: web.Request) -> web.Response:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_status = "ok"
    try:
        client = aioredis.from_url(redis_url)
        await client.ping()
        await client.aclose()
    except Exception as exc:
        logger.warning("Redis health check failed: %s", exc)
        redis_status = "error"

    return web.json_response(
        {
            "status": "ok",
            "service": "broker-worker",
            "version": "0.1.0",
            "dependencies": {"redis": redis_status},
        }
    )


async def start_health_server() -> None:
    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("broker-worker health server listening on :8080")
    await asyncio.Event().wait()
