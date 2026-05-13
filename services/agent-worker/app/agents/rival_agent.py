import logging
from app.agents.state import RivalAgentState
from app.errors import WorkflowError
from app.tools.rival_agent_tools.competitor_discovery.tools_discovery import run_competitor_discovery_tool
from app.tools.rival_agent_tools.competitor_research.tools_competitor import run_competitor_research_tool
from app.tools.rival_agent_tools.market_gap_analyzer.market_gap_analyzer import MarketGapAnalyzer, MarketGapInput
from app.tools.rival_agent_tools.smart_pricing_engine.smart_pricing_engine import PricingInput, SmartPricingEngine
from app.tools.rival_agent_tools.vision_synthesis.tools_synthesis import run_vision_synthesis_tool

logger = logging.getLogger(__name__)
_market_gap_analyzer = MarketGapAnalyzer()
_smart_pricing_engine = SmartPricingEngine()

class RivalAgent:
    async def discover_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        user_product = state["user_product"]

        try:
            result = await run_competitor_discovery_tool(
                platform=state["target_platform"],
                category=user_product.get("category", ""),
                product_title=user_product.get("title", ""),
                brand=state["brand"],
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success or not result.data:
            logger.warning("Competitor discovery returned no results | task_id=%s, continuing with empty list", task_id)
            return {**state, "competitor_names": []}

        competitor_names = [c.model_dump() for c in result.data.competitors]
        return {**state, "competitor_names": competitor_names}

    async def research_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        competitors = state["competitor_names"]
        category = state["user_product"].get("category", "")

        try:
            results = await run_competitor_research_tool(competitors, category)
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        competitor_research_results = [r.data.model_dump() for r in results if r.success and r.data]
        return {**state, "competitor_research_results": competitor_research_results}

    async def vision_synthesis(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        user_image_urls: list[str] = state["user_product"].get("image_urls", [])
        competitor_image_urls: list[str] = []
        for result in state["competitor_research_results"]:
            competitor_image_urls.extend(result.get("image_urls", []))

        try:
            analysis = await run_vision_synthesis_tool(
                user_image_urls,
                competitor_image_urls,
                variants=state.get("variants") or [],
            )
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
