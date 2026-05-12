import os

from pydantic import BaseModel


class RagInput(BaseModel):
    query: str
    top_k: int = 5


class RagOutput(BaseModel):
    documents: list[str]
    scores: list[float]


class RagContextTool:
    def __init__(
        self,
        collection_name: str,
        chroma_host: str = os.getenv("CHROMA_HOST", "localhost"),
    ) -> None:
        self.collection_name = collection_name
        self.chroma_host = chroma_host

    async def run(self, input: RagInput) -> RagOutput:
        return RagOutput(documents=[], scores=[])
