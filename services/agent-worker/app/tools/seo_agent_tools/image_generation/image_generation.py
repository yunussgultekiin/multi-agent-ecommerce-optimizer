from pydantic import BaseModel
from app.core import ToolResult

class ImageGenerationInput(BaseModel):
    generation_prompt: str
    target_platform: str

class ImageGenerationTool:
    async def run(self, input: ImageGenerationInput) -> ToolResult:
        raise NotImplementedError
