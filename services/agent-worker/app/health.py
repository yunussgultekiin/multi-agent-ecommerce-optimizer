from aiohttp import web


async def health_handler(request: web.Request) -> web.Response:
    return web.json_response(
        {
            "status": "ok",
            "service": "agent-worker",
            "version": "0.1.0",
        }
    )
