from pydantic import BaseModel, Field, field_validator

class Cluster(BaseModel):
    label: str
    competitors: list[str] = Field(default_factory=list)
    price_range_min: float = 0.0
    price_range_max: float = 0.0

class BrandLandscape(BaseModel):
    premium_brands: list[str] = Field(default_factory=list)
    budget_brands: list[str] = Field(default_factory=list)
    user_brand_position: str

class MarketGapResult(BaseModel):
    clusters: list[Cluster] = Field(..., min_length=1)
    user_product_cluster: str
    gap_opportunities: list[str] = Field(..., min_length=1)
    sentiment_based_opportunities: list[str] = Field(default_factory=list)
    trend_based_opportunities: list[str] = Field(default_factory=list)
    strategic_actions: list[str] = Field(default_factory=list)
    brand_landscape: BrandLandscape
    positioning_score: float = Field(..., ge=0.0, le=1.0)
    positioning_rationale: str = Field(..., min_length=1)
    variant_gap_opportunities: list[str] = Field(default_factory=list)

    @field_validator("positioning_rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("positioning_rationale cannot be empty")
        return value
