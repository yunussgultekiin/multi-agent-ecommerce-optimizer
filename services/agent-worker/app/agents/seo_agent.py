import logging
from app.agents.state import SeoAgentState
from app.task_client import TaskServiceClient

logger = logging.getLogger(__name__)
_task_client = TaskServiceClient()

class SeoAgent:
    async def retrieve_context(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def generate_seo(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def generate_image(self, state: SeoAgentState) -> SeoAgentState:
        return state

    async def finalize(self, state: SeoAgentState) -> SeoAgentState:
        final_result = {
            "seo_output": state.get("seo_output", {}),
            "generated_image_url": state.get("generated_image_url"),
            "rival_json": state.get("rival_json", {}),
        }
        await _task_client.save_result(state["task_id"], final_result)
        return {**state, "final_result": final_result, "status": "completed"}
