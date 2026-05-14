import logging
from app.agents.state import RivalAgentState
from app.core import WorkflowError
from app.task_client import TaskServiceClient
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.seo_graph import build_seo_state_from_rival, compiled_seo_graph
from app.tools.rival_agent_tools import (
    run_competitor_discovery_tool,
    run_competitor_research_tool,
    MarketGapAnalyzer,
    MarketGapInput,
    PricingInput,
    SmartPricingEngine,
    run_vision_synthesis_tool,
)

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
            logger.warning(
                "Competitor discovery returned no results | task_id=%s, continuing with empty list",
                task_id,
            )
            return {**state, "competitor_names": []}

        competitor_names = result.data["competitors"]
        return {**state, "competitor_names": competitor_names}

    async def research_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        competitors = state["competitor_names"]
        category = state["user_product"].get("category", "")

        try:
            results = await run_competitor_research_tool(competitors, category)
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        competitor_research_results = [
            {"success": r.success, "data": r.data, "fallback_used": r.fallback_used}
            for r in results
        ]

        return {
            **state,
            "competitor_research_results": competitor_research_results,
        }

    async def vision_synthesis(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]

        try:
            result = await run_vision_synthesis_tool(
                user_product=state["user_product"],
                competitor_research_results=state["competitor_research_results"],
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        return {**state, "vision_result": result.data}

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
            raise WorkflowError(
                f"Market gap analysis failed: {result.data}",
                task_id=task_id,
            )

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
            raise WorkflowError(
                f"Pricing analysis failed: {result.data}",
                task_id=task_id,
            )

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

        updated_state = {
            **state,
            "rival_json": rival_json,
        }

        seo_state = build_seo_state_from_rival(updated_state)
        seo_handler = WorkflowErrorHandler(compiled_seo_graph, TaskServiceClient())
        seo_final_state = await seo_handler.run(seo_state)

        seo_status = seo_final_state.get("status", "completed")
        if seo_status in ("failed", "cancelled"):
            return {
                **updated_state,
                "status": seo_status,
                "error": seo_final_state.get("error", ""),
                "cancelled": seo_final_state.get("cancelled", False),
            }

        return {
            **updated_state,
            "status": "completed",
        }