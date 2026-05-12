from typing import TypedDict


class WorkflowState(TypedDict):
    task_id: str
    product_data: dict
    competitor_data: list[dict]
    trend_data: dict
    market_gaps: list[str]
    vision_insights: dict
    pricing_suggestion: float | None
    rag_context: list[str]
    seo_output: dict
    errors: list[str]
    status: str
