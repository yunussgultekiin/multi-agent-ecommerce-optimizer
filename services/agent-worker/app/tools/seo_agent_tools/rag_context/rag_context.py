from pydantic import BaseModel
from app.tool_result import ToolResult

class RagContextInput(BaseModel):
    query: str
    target_platform: str

class RagContextTool:
    async def run(self, input: RagContextInput) -> ToolResult:
        raise NotImplementedError
