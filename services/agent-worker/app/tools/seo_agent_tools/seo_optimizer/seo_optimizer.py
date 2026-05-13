from pydantic import BaseModel
from app.tool_result import ToolResult

class SeoOptimizerInput(BaseModel):
    rival_json: dict
    rag_context: list[str]
    target_platform: str

class SeoOptimizerTool:
    async def run(self, input: SeoOptimizerInput) -> ToolResult:
        raise NotImplementedError
