from pydantic import BaseModel


class PricingInput(BaseModel):
    features: list[float]
    competitor_prices: list[float]


class PricingOutput(BaseModel):
    suggested_price: float
    confidence: float


class SmartPricingEngine:
    async def run(self, input: PricingInput) -> PricingOutput:
        return PricingOutput(suggested_price=0.0, confidence=0.0)
