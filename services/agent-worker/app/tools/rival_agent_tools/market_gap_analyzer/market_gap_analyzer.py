from pydantic import BaseModel
from app.tool_result import ToolResult

class MarketGapInput(BaseModel):
    competitor_research_results: list[dict]
    user_product: dict

class MarketGapAnalyzer:
    async def run(self, input: MarketGapInput) -> ToolResult:
        raise NotImplementedError
