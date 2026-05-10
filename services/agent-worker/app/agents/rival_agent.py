import logging

from app.agents.state import WorkflowState
from app.tools import MarketGapAnalyzer, SmartPricingEngine, TrendsTool, VisionTool, WebScraperTool
from app.tools.market_gap_analyzer import MarketGapInput
from app.tools.smart_pricing import PricingInput
from app.tools.trends import TrendsInput
from app.tools.vision import VisionInput
from app.tools.web_scraper import WebScraperInput

logger = logging.getLogger(__name__)


class RivalAgent:
    def __init__(self) -> None:
        self.scraper = WebScraperTool()
        self.trends = TrendsTool()
        self.market_gap = MarketGapAnalyzer()
        self.vision = VisionTool()
        self.pricing = SmartPricingEngine()

    async def run(self, state: WorkflowState) -> WorkflowState:
        state["status"] = "running"

        try:
            result = await self.scraper.run(WebScraperInput(url=""))
            state["competitor_data"] = result.pages
        except Exception as exc:
            logger.warning("WebScraperTool failed: %s", exc)
            state["errors"].append(f"web_scraper: {exc}")

        try:
            result = await self.trends.run(TrendsInput(keywords=[]))
            state["trend_data"] = result.interest_over_time
        except Exception as exc:
            logger.warning("TrendsTool failed: %s", exc)
            state["errors"].append(f"trends: {exc}")

        try:
            result = await self.market_gap.run(
                MarketGapInput(competitor_products=[], our_categories=[])
            )
            state["market_gaps"] = result.gaps
        except Exception as exc:
            logger.warning("MarketGapAnalyzer failed: %s", exc)
            state["errors"].append(f"market_gap: {exc}")

        try:
            result = await self.vision.run(VisionInput(image_url=""))
            state["vision_insights"] = {
                "description": result.description,
                "labels": result.detected_labels,
            }
        except Exception as exc:
            logger.warning("VisionTool failed: %s", exc)
            state["errors"].append(f"vision: {exc}")

        try:
            result = await self.pricing.run(
                PricingInput(features=[], competitor_prices=[])
            )
            state["pricing_suggestion"] = result.suggested_price
        except Exception as exc:
            logger.warning("SmartPricingEngine failed: %s", exc)
            state["errors"].append(f"pricing: {exc}")

        return state
