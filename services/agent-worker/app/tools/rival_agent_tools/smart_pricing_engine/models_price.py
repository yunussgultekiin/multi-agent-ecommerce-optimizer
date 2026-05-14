from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Positioning(str, Enum):
    underpriced = "underpriced"
    optimal = "optimal"
    overpriced = "overpriced"

class VariantPricing(BaseModel):
    variant_name: str
    base_price: float
    price_delta: float
    suggested_price: float
    positioning: Positioning

class CompetitorVariantOverlap(BaseModel):
    variant_name: str
    matching_competitors: list[str]

class PricingResult(BaseModel):
    price_median: float
    price_q1: float
    price_q3: float
    predicted_price: float
    price_range_min: float
    price_range_max: float
    positioning: Positioning
    positioning_score: float = Field(..., ge = 0.0, le = 1.0)
    market_power_gap: str
    confidence_score: float = Field(..., ge = 0.0, le = 1.0)
    fallback_used: bool = False
    variant_pricing: list[VariantPricing] = Field(default_factory = list)
    competitor_variant_overlap: list[CompetitorVariantOverlap] = Field(default_factory = list)
