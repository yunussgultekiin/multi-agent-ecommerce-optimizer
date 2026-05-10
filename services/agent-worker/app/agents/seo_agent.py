import logging

from app.agents.state import WorkflowState
from app.tools import RagContextTool, SeoOptimizerTool
from app.tools.rag_context import RagInput
from app.tools.seo_optimizer import SeoInput

logger = logging.getLogger(__name__)


class SeoAgent:
    def __init__(self) -> None:
        self.rag = RagContextTool(collection_name="products")
        self.seo = SeoOptimizerTool()

    async def run(self, state: WorkflowState) -> WorkflowState:
        try:
            result = await self.rag.run(RagInput(query=str(state.get("product_data", {}))))
            state["rag_context"] = result.documents
        except Exception as exc:
            logger.warning("RagContextTool failed: %s", exc)
            state["errors"].append(f"rag_context: {exc}")

        try:
            result = await self.seo.run(
                SeoInput(
                    product_title="",
                    description="",
                    keywords=[],
                    competitor_data=state.get("competitor_data", []),
                )
            )
            state["seo_output"] = {
                "title": result.optimized_title,
                "description": result.optimized_description,
                "tags": result.suggested_tags,
                "score": result.score,
            }
        except Exception as exc:
            logger.warning("SeoOptimizerTool failed: %s", exc)
            state["errors"].append(f"seo_optimizer: {exc}")

        state["status"] = "completed"
        return state
