import logging

from langgraph.graph import END, START, StateGraph

from app.agents.rival_agent import RivalAgent
from app.agents.seo_agent import SeoAgent
from app.agents.state import WorkflowState

logger = logging.getLogger(__name__)

_rival = RivalAgent()
_seo = SeoAgent()

_graph: StateGraph = StateGraph(WorkflowState)
_graph.add_node("rival_agent", _rival.run)
_graph.add_node("seo_agent", _seo.run)
_graph.add_edge(START, "rival_agent")
_graph.add_edge("rival_agent", "seo_agent")
_graph.add_edge("seo_agent", END)
compiled_graph = _graph.compile()


async def run_workflow(payload: dict) -> None:
    state: WorkflowState = {
        "task_id": payload.get("task_id", ""),
        "product_data": payload.get("product_data", {}),
        "competitor_data": [],
        "trend_data": {},
        "market_gaps": [],
        "vision_insights": {},
        "pricing_suggestion": None,
        "rag_context": [],
        "seo_output": {},
        "errors": [],
        "status": "pending",
    }
    try:
        final_state = await compiled_graph.ainvoke(state)
        logger.info(
            "Workflow completed: task_id=%s status=%s errors=%s",
            final_state.get("task_id"),
            final_state.get("status"),
            final_state.get("errors"),
        )
    except Exception as exc:
        logger.error("Workflow failed for task_id=%s: %s", state["task_id"], exc)
