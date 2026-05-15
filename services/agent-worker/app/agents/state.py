from typing import TypedDict

class BaseAgentState(TypedDict):
    task_id: str
    status: str
    error: str
    cancelled: bool

class RivalAgentState(BaseAgentState):
    user_product: dict
    competitor_names: list[dict]
    target_platform: str
    competitor_research_results: list[dict]
    sentiment_result: dict
    trend_result: dict
    gap_result: dict
    pricing_result: dict
    rival_json: dict


class SeoAgentState(BaseAgentState):
    rival_json: dict
    user_product: dict
    target_platform: str
    seo_output: dict
    generated_image_url: str | None
    final_result: dict
