from pydantic import BaseModel


class MarketGapInput(BaseModel):
    competitor_products: list[dict]
    our_categories: list[str]


class MarketGapOutput(BaseModel):
    gaps: list[str]
    cluster_labels: list[int]


class MarketGapAnalyzer:
    async def run(self, input: MarketGapInput) -> MarketGapOutput:
        return MarketGapOutput(gaps=[], cluster_labels=[])
