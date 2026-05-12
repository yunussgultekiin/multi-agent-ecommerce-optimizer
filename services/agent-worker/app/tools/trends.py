from pydantic import BaseModel


class TrendsInput(BaseModel):
    keywords: list[str]
    timeframe: str = "today 3-m"


class TrendsOutput(BaseModel):
    interest_over_time: dict
    related_queries: dict


class TrendsTool:
    async def run(self, input: TrendsInput) -> TrendsOutput:
        return TrendsOutput(interest_over_time={}, related_queries={})
