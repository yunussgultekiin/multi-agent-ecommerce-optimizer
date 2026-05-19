import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)
_REMOVEBG_URL = "https://api.remove.bg/v1.0/removebg"

async def remove_background(image_bytes: bytes) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            _REMOVEBG_URL,
            headers={"X-Api-Key": settings.removebg_api_key},
            params={"size": "auto", "format": "png"},
            files={
                "image_file": (
                    "product.png",
                    image_bytes,
                    "application/octet-stream",
                )
            },
        )
        response.raise_for_status()
        output_bytes = response.content
        logger.info("removebg complete | output_size=%d", len(output_bytes))
        return output_bytes