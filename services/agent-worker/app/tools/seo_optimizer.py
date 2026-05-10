import logging
import os

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SeoInput(BaseModel):
    product_title: str
    description: str
    keywords: list[str]
    competitor_data: list[dict]


class SeoOutput(BaseModel):
    optimized_title: str
    optimized_description: str
    suggested_tags: list[str]
    score: float


class SeoOptimizerTool:
    def __init__(self, gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")) -> None:
        self.gemini_api_key = gemini_api_key
        if not self.gemini_api_key:
            logger.warning("SeoOptimizerTool: GEMINI_API_KEY not set")

    async def run(self, input: SeoInput) -> SeoOutput:
        return SeoOutput(
            optimized_title="",
            optimized_description="",
            suggested_tags=[],
            score=0.0,
        )
