import logging
from langgraph.graph import END, START, StateGraph
from app.agents.rival_agent import RivalAgent
from app.agents.state import RivalAgentState
from app.task_client import TaskServiceClient
from app.workflow.error_handler import WorkflowErrorHandler
from app.workflow.node_runner import NodeRunner

logger = logging.getLogger(__name__)
_rival_agent = RivalAgent()
_task_client = TaskServiceClient()


def _cancel_or(next_node: str):
    def route(state: RivalAgentState) -> str:
        return END if state.get("cancelled") else next_node
    return route


def _build_rival_graph():
    graph = StateGraph(RivalAgentState)

    graph.add_node(
        "discover_competitors",
        NodeRunner("competitor_discovery", 10).wrap(_rival_agent.discover_competitors),
    )
    graph.add_node(
        "research_competitors",
        NodeRunner("competitor_research", 25).wrap(_rival_agent.research_competitors),
    )
    graph.add_node(
        "analyze_sentiment",
        NodeRunner("sentiment_analysis", 40).wrap(_rival_agent.analyze_sentiment),
    )
    graph.add_node(
        "analyze_trends",
        NodeRunner("trend_analysis", 55).wrap(_rival_agent.analyze_trends),
    )
    graph.add_node(
        "market_gap",
        NodeRunner("market_gap", 70).wrap(_rival_agent.market_gap),
    )
    graph.add_node(
        "pricing",
        NodeRunner("smart_pricing", 85).wrap(_rival_agent.pricing),
    )
    graph.add_node(
        "finalize",
        NodeRunner("finalize", 100).wrap(_rival_agent.finalize),
    )

    graph.add_edge(START, "discover_competitors")
    graph.add_conditional_edges("discover_competitors", _cancel_or("research_competitors"))
    graph.add_conditional_edges("research_competitors", _cancel_or("analyze_sentiment"))
    graph.add_conditional_edges("analyze_sentiment", _cancel_or("analyze_trends"))
    graph.add_conditional_edges("analyze_trends", _cancel_or("market_gap"))
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
        sentiment_result={},
        trend_result={},
        gap_result={},
        pricing_result={},
        rival_json={},
        error="",
        status="pending",
        cancelled=False,
    )


async def run_rival_workflow(payload: dict) -> None:
    state = _build_rival_initial_state(payload)
    handler = WorkflowErrorHandler(_compiled_rival_graph, _task_client)
    await handler.run(state)
