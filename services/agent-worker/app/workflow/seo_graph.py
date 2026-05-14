import logging
from langgraph.graph import END, START, StateGraph
from app.agents.seo_agent import SeoAgent
from app.agents.state import RivalAgentState, SeoAgentState
from app.task_client import TaskServiceClient
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.node_runner import NodeRunner

logger = logging.getLogger(__name__)
_seo_agent = SeoAgent()
_task_client = TaskServiceClient()

def _cancel_or(*next_nodes: str):
    def route(state: SeoAgentState) -> str | list[str]:
        if state.get("cancelled"): return END
        if len(next_nodes) == 1: return next_nodes[0]
        return list(next_nodes)
    return route

def _build_seo_graph():
    graph = StateGraph(SeoAgentState)

    graph.add_node(
        "retrieve_context",
        NodeRunner("retrieve_context", 25).wrap(_seo_agent.retrieve_context),
    )
    graph.add_node(
        "generate_seo",
        NodeRunner("generate_seo", 60).wrap(_seo_agent.generate_seo),
    )
    graph.add_node(
        "generate_image",
        NodeRunner("generate_image", 85).wrap(_seo_agent.generate_image),
    )
    graph.add_node(
        "finalize",
        NodeRunner("finalize", 100).wrap(_seo_agent.finalize),
    )

    graph.add_edge(START, "retrieve_context")
    graph.add_conditional_edges(
        "retrieve_context",
        _cancel_or("generate_seo", "generate_image"),
    )
    graph.add_conditional_edges(
        "generate_seo",
        _cancel_or("finalize"),
    )
    graph.add_conditional_edges(
        "generate_image",
        _cancel_or("finalize"),
    )
    graph.add_edge("finalize", END)

    return graph.compile()

compiled_seo_graph = _build_seo_graph()

def build_seo_state_from_rival(rival_state: RivalAgentState) -> SeoAgentState:
    return SeoAgentState(
        task_id=rival_state["task_id"],
        rival_json=rival_state.get("rival_json", {}),
        target_platform=rival_state.get("target_platform", ""),
        generation_prompt=rival_state.get("vision_result", {}).get("generation_prompt", ""),
        rag_context=[],
        seo_output={},
        generated_image_url=None,
        final_result={},
        error="",
        status="pending",
        cancelled=False,
    )

def _build_seo_initial_state(payload: dict) -> SeoAgentState:
    return SeoAgentState(
        task_id=payload.get("task_id", ""),
        rival_json=payload.get("rival_json", {}),
        target_platform=payload.get("target_platform", ""),
        generation_prompt=payload.get("generation_prompt", ""),
        rag_context=[],
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