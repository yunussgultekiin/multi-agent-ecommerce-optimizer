from app.agents.state import RivalAgentState
from app.core import ToolResult, WorkflowError
from app.task_client import TaskServiceClient
from app.tools.rival_agent_tools import (
    IDEAL_RESEARCH_COUNT,
    MIN_VALID_COMPETITORS,
    run_competitor_discovery_tool,
    run_competitor_research_tool,
    run_market_gap_analyzer,
    run_sentiment_analyzer,
    run_smart_pricing_engine,
    run_trend_analyzer,
)
from app.tools.rival_agent_tools.competitor_discovery.models_discovery import (
    PRIMARY_RELEVANCE_THRESHOLD,
    RELEVANCE_THRESHOLD,
    SECONDARY_RELEVANCE_THRESHOLD,
)
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.seo_graph import build_seo_state_from_rival, compiled_seo_graph
import logging

logger = logging.getLogger(__name__)

def _to_tool_results(research_results: list[dict]) -> list[ToolResult]:
    return [
        ToolResult(
            success=r.get("success", False),
            data=r.get("data") or {},
            fallback_used=r.get("fallback_used", False),
        )
        for r in research_results
    ]


def _build_discovery_lookup(competitor_names: list[dict]) -> dict[str, dict]:
    """competitor_name → discovery dict (similarity bilgisi için)."""
    return {
        c.get("competitor_name", "").lower().strip(): c
        for c in competitor_names
        if c.get("competitor_name")
    }


def _get_relevant_research(state: RivalAgentState) -> list[dict]:
    lookup = _build_discovery_lookup(state.get("competitor_names", []))
    all_results = state["competitor_research_results"]

    def _score(r: dict) -> int:
        name = (r.get("data") or {}).get("competitor_name", "").lower().strip()
        return lookup.get(name, {}).get("similarity_score", 0)

    primary = [r for r in all_results if _score(r) >= PRIMARY_RELEVANCE_THRESHOLD]
    if len(primary) >= MIN_VALID_COMPETITORS:
        logger.info(
            "Relevant competitors selected (primary) | count=%d threshold=%d",
            len(primary), PRIMARY_RELEVANCE_THRESHOLD,
        )
        return primary

    secondary = [r for r in all_results if _score(r) >= SECONDARY_RELEVANCE_THRESHOLD]
    if len(secondary) >= MIN_VALID_COMPETITORS:
        logger.warning(
            "Primary tier insufficient (%d), using secondary | count=%d threshold=%d",
            len(primary), len(secondary), SECONDARY_RELEVANCE_THRESHOLD,
        )
        return secondary

    sorted_all = sorted(all_results, key=_score, reverse=True)
    n = max(MIN_VALID_COMPETITORS, len(all_results) // 2 + 1)
    top_n = sorted_all[:n]
    logger.warning(
        "Insufficient relevant competitors (primary=%d secondary=%d) — using top-%d by score",
        len(primary), len(secondary), len(top_n),
    )
    return top_n

class RivalAgent:
    async def discover_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        user_product = state["user_product"]

        try:
            result = await run_competitor_discovery_tool(
                platform=state["target_platform"],
                category=user_product.get("category", ""),
                product_title=user_product.get("title", ""),
                brand=state["user_product"].get("brand", ""),
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success or not result.data:
            raise WorkflowError(
                "Competitor discovery returned no results. Cannot proceed without competitor data.",
                task_id=task_id,
            )

        return {**state, "competitor_names": result.data["competitors"]}

    async def research_competitors(self, state: RivalAgentState) -> RivalAgentState:
        task_id = state["task_id"]
        competitors = state["competitor_names"]
        category = state["user_product"].get("category", "")

        try:
            results = await run_competitor_research_tool(competitors, category)
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        successful_count = sum(1 for r in results if r.success)

        if successful_count < MIN_VALID_COMPETITORS:
            raise WorkflowError(
                f"Insufficient competitor data: only {successful_count} of {len(results)} researched successfully",
                task_id=task_id,
            )

        if successful_count < IDEAL_RESEARCH_COUNT:
            logger.warning(
                "Partial competitor research | task_id=%s successful=%d/%d fallback_mode=True",
                task_id,
                successful_count,
                len(results),
            )

        competitor_research_results = [
            {"success": r.success, "data": r.data, "fallback_used": r.fallback_used}
            for r in results
        ]

        return {**state, "competitor_research_results": competitor_research_results}

    async def analyze_sentiment(self, state: RivalAgentState) -> dict:
        task_id = state["task_id"]

        try:
            result = await run_sentiment_analyzer(
                competitor_names=state["competitor_names"],
                competitor_research_results=state["competitor_research_results"],
                category=state["user_product"].get("category", ""),
                target_platform=state["target_platform"],
                user_product=state["user_product"],
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success:
            logger.warning(
                "SentimentAnalyzerTool failed, continuing with empty sentiment | task_id=%s error=%s",
                task_id,
                result.data.get("error"),
            )
            return {"sentiment_result": {}}

        return {"sentiment_result": result.data}

    async def analyze_trends(self, state: RivalAgentState) -> dict:
        task_id = state["task_id"]

        try:
            result = await run_trend_analyzer(
                category=state["user_product"].get("category", ""),
                target_platform=state["target_platform"],
                user_product=state["user_product"],
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success:
            logger.warning(
                "TrendAnalyzerTool failed, continuing with empty trend | task_id=%s error=%s",
                task_id,
                result.data.get("error"),
            )
            return {"trend_result": {}}

        return {"trend_result": result.data}

    async def market_gap(self, state: RivalAgentState) -> dict:
        task_id = state["task_id"]

        try:
            relevant_research = _get_relevant_research(state)
            result = await run_market_gap_analyzer(
                user_product=state["user_product"],
                competitor_tool_results=_to_tool_results(relevant_research),
                sentiment_result=state.get("sentiment_result") or {},
                trend_result=state.get("trend_result") or {},
            )
        except Exception as exc:
            logger.warning(
                "MarketGapAnalyzer raised exception, continuing with empty gap | task_id=%s error=%s",
                task_id,
                exc,
            )
            return {"gap_result": {}}

        if not result.success:
            logger.warning(
                "MarketGapAnalyzer failed, continuing with empty gap | task_id=%s error=%s",
                task_id,
                result.data.get("error"),
            )
            return {"gap_result": {}}

        return {"gap_result": result.data}

    async def pricing(self, state: RivalAgentState) -> dict:
        task_id = state["task_id"]

        try:
            relevant_research = _get_relevant_research(state)
            result = await run_smart_pricing_engine(
                user_product=state["user_product"],
                competitor_tool_results=_to_tool_results(relevant_research),
                gap_result=state.get("gap_result"),
                sentiment_result=state.get("sentiment_result") or {},
                trend_result=state.get("trend_result") or {},
                target_platform=state.get("target_platform", ""),
            )
        except Exception as exc:
            raise WorkflowError(str(exc), task_id=task_id)

        if not result.success:
            raise WorkflowError(
                f"Pricing analysis failed: {result.data}",
                task_id=task_id,
            )

        return {"pricing_result": result.data}

    async def finalize(self, state: RivalAgentState) -> RivalAgentState:
        lookup = _build_discovery_lookup(state.get("competitor_names", []))
        enriched_research = []
        for r in state["competitor_research_results"]:
            comp_name = (r.get("data") or {}).get("competitor_name", "").lower().strip()
            discovery = lookup.get(comp_name, {})
            enriched = dict(r)
            if discovery:
                score = discovery.get("similarity_score", 50)
                enriched["similarity_score"] = score
                enriched["similarity_label"] = discovery.get("similarity_label", "Orta")
                enriched["similarity_reason"] = discovery.get(
                    "similarity_reason",
                    discovery.get("reason", ""),
                )
                enriched["is_relevant"] = score >= RELEVANCE_THRESHOLD
            enriched_research.append(enriched)

        rival_json = {
            "user_product": state["user_product"],
            "target_platform": state["target_platform"],
            "competitors": state["competitor_names"],
            "competitor_research_results": enriched_research,
            "sentiment_result": state.get("sentiment_result") or {},
            "trend_result": state.get("trend_result") or {},
            "gap_result": state.get("gap_result") or {},
            "pricing_result": state.get("pricing_result") or {},
        }

        updated_state = {**state, "rival_json": rival_json}

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

        return {**updated_state, "status": "completed"}
