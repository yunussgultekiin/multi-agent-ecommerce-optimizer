import asyncio
import logging
from aiohttp import web
from app.config import settings
from app.redis import close_redis
from app.workflow.rival_graph import run_rival_workflow
from app.workflow.seo_graph import run_seo_workflow

logger = logging.getLogger(__name__)

_AGENT_RUNNERS = {
    "rival": run_rival_workflow,
    "seo": run_seo_workflow,
}

async def run_handler(request: web.Request) -> web.Response:
    agent_type = request.match_info["agent_type"]
    if agent_type not in _AGENT_RUNNERS:
        return web.json_response(
            {"error": f"Unknown agent_type '{agent_type}'. Must be one of: {list(_AGENT_RUNNERS)}"},
            status=400,
        )
    payload = await request.json()
    asyncio.create_task(_AGENT_RUNNERS[agent_type](payload))
    return web.json_response({"status": "accepted", "agent_type": agent_type}, status=202)

async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "agent-worker", "version": "0.1.0"})

async def on_shutdown(app: web.Application) -> None:
    await close_redis()

async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    app = web.Application()
    app.router.add_post("/run/{agent_type}", run_handler)
    app.router.add_get("/health", health_handler)
    app.on_shutdown.append(on_shutdown)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("agent-worker listening on :8080")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
