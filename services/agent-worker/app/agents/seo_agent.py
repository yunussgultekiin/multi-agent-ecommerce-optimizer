import logging
from app.agents.state import SeoAgentState
from app.task_client import TaskServiceClient

logger = logging.getLogger(__name__)
_task_client = TaskServiceClient()

class SeoAgent:
    async def retrieve_context(self, state: SeoAgentState) -> SeoAgentState:
        platform = state.get("target_platform", "")
        rag_context = [
            f"Platform: {platform}",
            "Optimize for product discoverability and conversion rate.",
            "Use platform-specific best practices for title length and keyword density.",
        ]
        return {**state, "rag_context": rag_context}

    async def generate_seo(self, state: SeoAgentState) -> SeoAgentState:
        rival_json = state.get("rival_json", {})
        user_product = rival_json.get("user_product", {})
        platform = state.get("target_platform", "")
        title = user_product.get("title", "Product")
        category = user_product.get("category", "")
        features = user_product.get("features", [])
        keywords = [category] + features[:3] if category else features[:3]
        seo_output = {
            "title": title,
            "description": f"Premium {category} product optimized for {platform}. {title}.",
            "bullet_points": features[:5],
            "keywords": keywords,
        }
        return {**state, "seo_output": seo_output}

    async def generate_image(self, state: SeoAgentState) -> SeoAgentState:
        return {**state, "generated_image_url": None}

    async def finalize(self, state: SeoAgentState) -> SeoAgentState:
        final_result = {
            "seo_output": state.get("seo_output", {}),
            "generated_image_url": state.get("generated_image_url"),
            "rival_json": state.get("rival_json", {}),
        }
        await _task_client.save_result(state["task_id"], final_result)
        await _task_client.update_status(state["task_id"], "completed")
        return {**state, "final_result": final_result, "status": "completed"}
