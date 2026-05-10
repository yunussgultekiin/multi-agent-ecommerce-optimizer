from pydantic import BaseModel


class WebScraperInput(BaseModel):
    url: str
    max_pages: int = 5


class WebScraperOutput(BaseModel):
    pages: list[dict]
    scraped_at: str


class WebScraperTool:
    async def run(self, input: WebScraperInput) -> WebScraperOutput:
        return WebScraperOutput(pages=[], scraped_at="")
