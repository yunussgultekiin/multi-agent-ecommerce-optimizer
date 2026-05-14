from pydantic import BaseModel
from app.core import ToolResult

class PricingInput(BaseModel):
    competitor_research_results: list[dict]
    user_product: dict

class SmartPricingEngine:
    async def run(self, input: PricingInput) -> ToolResult:
        raise NotImplementedError
