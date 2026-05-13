import asyncio
import logging
from app.agents.state import RivalAgentState
from app.errors import WorkflowError
from app.tools.Rival_Agent_tools.CompetitorResearch.competitor_research import CompetitorResearchInput, CompetitorResearchTool
from app.tools.Rival_Agent_tools.MarketGapAnalyzer.market_gap_analyzer import MarketGapAnalyzer, MarketGapInput
from app.tools.Rival_Agent_tools.SmartPricingEngine.smart_pricing_engine import PricingInput, SmartPricingEngine
from app.tools.Rival_Agent_tools.VisionSynthesis.tools_synthesis import run_vision_synthesis_tool

logger = logging.getLogger(__name__)

_competitor_research_tool = CompetitorResearchTool()
_market_gap_analyzer = MarketGapAnalyzer()
_smart_pricing_engine = SmartPricingEngine()

class RivalAgent:
    async def research_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        competitor_names = state["competitor_names"]
        target_platform = state["target_platform"]

        async def _research_one(name: str) -> dict:
            result = await _competitor_research_tool.run(
                CompetitorResearchInput(competitor_name=name, target_platform=target_platform)
            )
            if not result.success:
                logger.warning("Competitor research failed for %s: %s", name, result.data)
                return {}
            return result.data

        try:
            raw_results = await asyncio.gather(*[_research_one(name) for name in competitor_names])
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        competitor_research_results = [r for r in raw_results if r]
        return {**state, "competitor_research_results": competitor_research_results}

    async def vision_synthesis(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        user_image_urls: list[str] = state["user_product"].get("image_urls", [])
        competitor_image_urls: list[str] = []
        for result in state["competitor_research_results"]:
            competitor_image_urls.extend(result.get("image_urls", []))

        try:
            analysis = await run_vision_synthesis_tool(user_image_urls, competitor_image_urls)
            vision_result = analysis.model_dump()
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        return {**state, "vision_result": vision_result}

    async def market_gap(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        try:
            result = await _market_gap_analyzer.run(
                MarketGapInput(
                    competitor_research_results=state["competitor_research_results"],
                    user_product=state["user_product"],
                )
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success:
            raise WorkflowError(f"Market gap analysis failed: {result.data}", task_id=task_id)

        return {**state, "gap_result": result.data}

    async def pricing(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        try:
            result = await _smart_pricing_engine.run(
                PricingInput(
                    competitor_research_results=state["competitor_research_results"],
                    user_product=state["user_product"],
                )
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success:
            raise WorkflowError(f"Pricing analysis failed: {result.data}", task_id=task_id)

        return {**state, "pricing_result": result.data}

    async def finalize(self, state: RivalAgentState) -> RivalAgentState:
        rival_json = {
            "user_product": state["user_product"],
            "target_platform": state["target_platform"],
            "competitor_research_results": state["competitor_research_results"],
            "vision_result": state["vision_result"],
            "gap_result": state["gap_result"],
            "pricing_result": state["pricing_result"],
        }
        return {**state, "rival_json": rival_json, "status": "completed"}
