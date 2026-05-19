from app.agents.seo_agent import SeoAgent
from app.agents.state import RivalAgentState, SeoAgentState
from app.task_client import TaskServiceClient
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.node_runner import NodeRunner
from langgraph.graph import END, START, StateGraph
import logging

logger = logging.getLogger(__name__)
_seo_agent = SeoAgent()
_task_client = TaskServiceClient()

def _cancel_or(*next_nodes: str):
    def route(state: SeoAgentState) -> str | list[str]:
        if state.get("cancelled"):
            return END
        if len(next_nodes) == 1:
            return next_nodes[0]
        return list(next_nodes)

    return route

def _build_seo_graph():
    graph = StateGraph(SeoAgentState)

    graph.add_node(
        "generate_seo",
        NodeRunner("seo_optimization", 80).wrap(_seo_agent.generate_seo),
    )
    graph.add_node(
        "generate_image",
        NodeRunner("image_generation", 90).wrap(_seo_agent.generate_image),
    )
    graph.add_node(
        "finalize",
        NodeRunner("finalize", 100).wrap(_seo_agent.finalize),
    )

    graph.add_conditional_edges(START, _cancel_or("generate_seo", "generate_image"))
    graph.add_conditional_edges("generate_seo", _cancel_or("finalize"))
    graph.add_conditional_edges("generate_image", _cancel_or("finalize"))
    graph.add_edge("finalize", END)

    return graph.compile()

compiled_seo_graph = _build_seo_graph()

def build_seo_state_from_rival(rival_state: RivalAgentState) -> SeoAgentState:
    rival_json = rival_state.get("rival_json", {})
    return SeoAgentState(
        task_id=rival_state["task_id"],
        rival_json=rival_json,
        user_product=rival_json.get("user_product", {}),
        target_platform=rival_json.get("target_platform", "")
        or rival_state.get("target_platform", ""),
        seo_output={},
        generated_image_url=None,
        final_result={},
        error="",
        status="pending",
        cancelled=False,
    )

def _build_seo_initial_state(payload: dict) -> SeoAgentState:
    rival_json = payload.get("rival_json", {})
    return SeoAgentState(
        task_id=payload.get("task_id", ""),
        rival_json=rival_json,
        user_product=rival_json.get("user_product", {}),
        target_platform=payload.get("target_platform", "")
        or rival_json.get("target_platform", ""),
        seo_output={},
        generated_image_url=None,
        final_result={},
        error="",
        status="pending",
        cancelled=False,
    )

async def run_seo_workflow(payload: dict) -> None:
    state = _build_seo_initial_state(payload)
    handler = WorkflowErrorHandler(compiled_seo_graph, _task_client)
    await handler.run(state)
