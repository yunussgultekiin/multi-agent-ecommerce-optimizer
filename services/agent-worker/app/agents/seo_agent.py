import logging
from app.agents.state import SeoAgentState
from app.task_client import TaskServiceClient
from app.tools.seo_agent_tools.image_generation import ImageGenerationInput, ImageGenerationTool
from app.tools.seo_agent_tools.seo_optimizer import SeoOptimizerInput, SeoOptimizerTool

logger = logging.getLogger(__name__)
_task_client = TaskServiceClient()
_seo_optimizer = SeoOptimizerTool()
_image_tool = ImageGenerationTool()


class SeoAgent:
    async def retrieve_context(self, state: SeoAgentState) -> SeoAgentState:
        user_product = state.get("user_product", {})
        platform = state.get("target_platform", "")
        category = user_product.get("category", "")
        brand = user_product.get("brand", "")
        variants = [v.get("name", "") for v in user_product.get("variants", []) if isinstance(v, dict)]

        rag_context = [
            f"Platform: {platform}",
            f"Category: {category}" if category else "Category: general",
            f"Brand: {brand}" if brand else "",
            f"Variants: {', '.join(variants)}" if variants else "",
            "Optimize for product discoverability and conversion rate.",
            "Use platform-specific best practices for title length and keyword density.",
        ]
        rag_context = [line for line in rag_context if line]

        return {**state, "rag_context": rag_context}

    async def generate_seo(self, state: SeoAgentState) -> SeoAgentState:
        result = await _seo_optimizer.run(
            SeoOptimizerInput(
                rival_json=state.get("rival_json", {}),
                rag_context=state.get("rag_context", []),
                target_platform=state.get("target_platform", ""),
            )
        )

        if result.success:
            return {**state, "seo_output": result.data}

        logger.warning("SeoOptimizerTool failed, using empty seo_output | error=%s", result.data.get("error"))
        return {**state, "seo_output": result.data}

    async def generate_image(self, state: SeoAgentState) -> SeoAgentState:
        result = await _image_tool.run(
            ImageGenerationInput(
                user_product=state.get("user_product", {}),
                target_platform=state.get("target_platform", ""),
                rival_json=state.get("rival_json", {}),
            )
        )

        generated_url = result.data.get("generated_image_url") if result.data else None
        return {**state, "generated_image_url": generated_url}

    async def finalize(self, state: SeoAgentState) -> SeoAgentState:
        final_result = {
            "rival_json": state.get("rival_json", {}),
            "seo_output": state.get("seo_output", {}),
            "generated_image_url": state.get("generated_image_url"),
        }

        await _task_client.save_result(state["task_id"], final_result)

        return {**state, "final_result": final_result, "status": "completed"}
