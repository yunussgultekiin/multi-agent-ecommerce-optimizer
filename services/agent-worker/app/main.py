import asyncio
import logging

from aiohttp import web

from app.health import health_handler
from app.workflow.graph import run_workflow

logger = logging.getLogger(__name__)


async def run_handler(request: web.Request) -> web.Response:
    payload: dict = await request.json()
    asyncio.create_task(run_workflow(payload))
    return web.json_response({"status": "accepted"})


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = web.Application()
    app.router.add_post("/run", run_handler)
    app.router.add_get("/health", health_handler)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("agent-worker listening on :8080")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
