from pydantic import BaseModel, Field
from typing import Optional

class Cluster(BaseModel):
    label: str
    competitors: list[str]
    price_range_min: float
    price_range_max: float

class BrandLandscape(BaseModel):
    premium_brands: list[str] = Field(default_factory = list)
    budget_brands: list[str] = Field(default_factory = list)
    user_brand_position: str

class MarketGapResult(BaseModel):
    clusters: list[Cluster] = Field(..., min_length = 1)
    user_product_cluster: str
    gap_opportunities: list[str] = Field(..., min_length = 1)
    brand_landscape: BrandLandscape
    positioning_score: float = Field(..., ge = 0.0, le = 1.0)
    positioning_rationale: str = Field(..., min_length = 1)
    variant_gap_opportunities: list[str] = Field(default_factory = list)

class ToolResult(BaseModel):
    success: bool
    data: Optional[MarketGapResult] = None
    fallback_used: bool = False
    error: Optional[str] = None

