from pydantic import BaseModel
from app.tool_result import ToolResult

class CompetitorResearchInput(BaseModel):
    competitor_name: str
    target_platform: str

class CompetitorResearchTool:
    async def run(self, input: CompetitorResearchInput) -> ToolResult:
        raise NotImplementedError
