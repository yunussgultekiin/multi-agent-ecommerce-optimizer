import logging
import os

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class VisionInput(BaseModel):
    image_url: str
    prompt: str = "Describe this product image"


class VisionOutput(BaseModel):
    description: str
    detected_labels: list[str]


class VisionTool:
    def __init__(self, gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")) -> None:
        self.gemini_api_key = gemini_api_key
        if not self.gemini_api_key:
            logger.warning("VisionTool: GEMINI_API_KEY not set")

    async def run(self, input: VisionInput) -> VisionOutput:
        return VisionOutput(description="", detected_labels=[])
