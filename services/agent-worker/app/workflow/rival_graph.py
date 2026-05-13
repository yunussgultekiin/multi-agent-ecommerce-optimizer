import logging
from langgraph.graph import END, START, StateGraph
from app.agents.rival_agent import RivalAgent
from app.agents.state import RivalAgentState
from app.errors import WorkflowError
from app.progress import report_progress
from app.task_client import TaskServiceClient
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.node_runner import NodeRunner
from app.workflow.seo_graph import build_seo_state_from_rival, compiled_seo_graph

logger = logging.getLogger(__name__)
_rival_agent = RivalAgent()
_task_client = TaskServiceClient()

def _cancel_or(next_node: str):
    def route(state: RivalAgentState) -> str:
        return END if state.get("cancelled") else next_node
    return route

def _build_rival_graph():
    graph = StateGraph(RivalAgentState)
    graph.add_node("discover_competitors", NodeRunner("discover_competitors", 10).wrap(_rival_agent.discover_competitors))
    graph.add_node("research_competitors", NodeRunner("research_competitors", 30).wrap(_rival_agent.research_competitors))
    graph.add_node("vision_synthesis", NodeRunner("vision_synthesis", 50).wrap(_rival_agent.vision_synthesis))
    graph.add_node("market_gap", NodeRunner("market_gap", 70).wrap(_rival_agent.market_gap))
    graph.add_node("pricing", NodeRunner("pricing", 85).wrap(_rival_agent.pricing))
    graph.add_node("finalize", NodeRunner("finalize", 100).wrap(_rival_agent.finalize))
    graph.add_edge(START, "discover_competitors")
    graph.add_conditional_edges("discover_competitors", _cancel_or("research_competitors"))
    graph.add_conditional_edges("research_competitors", _cancel_or("vision_synthesis"))
    graph.add_conditional_edges("vision_synthesis", _cancel_or("market_gap"))
    graph.add_conditional_edges("market_gap", _cancel_or("pricing"))
    graph.add_conditional_edges("pricing", _cancel_or("finalize"))
    graph.add_edge("finalize", END)
    return graph.compile()

_compiled_rival_graph = _build_rival_graph()

def _build_rival_initial_state(payload: dict) -> RivalAgentState:
    inner = payload.get("payload", payload)
    user_product = inner.get("user_product", {})
    return RivalAgentState(
        task_id=payload.get("task_id", ""),
        user_product=user_product,
        competitor_names=[],
        target_platform=inner.get("target_platform", ""),
        competitor_research_results=[],
        vision_result={},
        gap_result={},
        pricing_result={},
        rival_json={},
        error="",
        status="pending",
        cancelled=False,
        brand=user_product.get("brand", ""),
        variants=user_product.get("variants", []),
    )

async def run_rival_workflow(payload: dict) -> None:
    state = _build_rival_initial_state(payload)
    task_id = state["task_id"]
    try:
        final_rival_state = await _compiled_rival_graph.ainvoke(state)
        terminal_status = final_rival_state.get("status", "")
        if terminal_status in ("failed", "cancelled"):
            error_message = final_rival_state.get("error") or None
            await _task_client.update_status(task_id, terminal_status, error_message=error_message)
            await report_progress(task_id, "rival_agent", terminal_status, 0)
            return
        seo_state = build_seo_state_from_rival(final_rival_state)
        seo_handler = WorkflowErrorHandler(compiled_seo_graph, _task_client)
        await seo_handler.run(seo_state)
    except WorkflowError as exc:
        logger.error("WorkflowError in rival | task_id=%s error=%s", task_id, exc)
        await _task_client.update_status(task_id, "failed", error_message=str(exc))
        await report_progress(task_id, "rival_agent", "failed", 0)
    except Exception as exc:
        logger.error("Unexpected error in rival | task_id=%s error=%s", task_id, exc)
        await _task_client.update_status(task_id, "failed", error_message=str(exc))
        await report_progress(task_id, "rival_agent", "failed", 0)
