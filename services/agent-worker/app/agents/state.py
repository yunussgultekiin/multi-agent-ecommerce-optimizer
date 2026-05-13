from typing import TypedDict

class BaseAgentState(TypedDict):
    task_id: str
    status: str
    error: str
    cancelled: bool

class RivalAgentState(BaseAgentState):
    user_product: dict
    competitor_names: list[str]
    target_platform: str
    competitor_research_results: list[dict]
    vision_result: dict
    gap_result: dict
    pricing_result: dict
    rival_json: dict

class SeoAgentState(BaseAgentState):
    rival_json: dict
    target_platform: str
    generation_prompt: str
    rag_context: list[str]
    seo_output: dict
    generated_image_url: str | None
    final_result: dict
