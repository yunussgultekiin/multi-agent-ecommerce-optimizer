from typing import Optional
from pydantic import BaseModel
from app.core import ToolResult


class PricingInput(BaseModel):
    competitor_research_results: list[dict]
    user_product: dict
    gap_result: Optional[dict] = None
    sentiment_result: Optional[dict] = None
    trend_result: Optional[dict] = None
    target_platform: str = ""


class SmartPricingEngine:
    async def run(self, input: PricingInput) -> ToolResult:
        from .tools_price import run_smart_pricing_engine

        tool_results = [
            ToolResult(
                success=r.get("success", False),
                data=r.get("data") or {},
                fallback_used=r.get("fallback_used", False),
            )
            for r in input.competitor_research_results
        ]

        return await run_smart_pricing_engine(
            user_product=input.user_product,
            competitor_tool_results=tool_results,
            gap_result=input.gap_result,
            sentiment_result=input.sentiment_result,
            trend_result=input.trend_result,
            target_platform=input.target_platform,
        )
