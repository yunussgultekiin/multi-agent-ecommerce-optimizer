from pydantic import BaseModel
from app.core import ToolResult

class RagContextInput(BaseModel):
    query: str
    target_platform: str

class RagContextTool:
    async def run(self, input: RagContextInput) -> ToolResult:
        raise NotImplementedError
