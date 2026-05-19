from pydantic import BaseModel, Field, field_validator, model_validator

class Cluster(BaseModel):
    label: str
    competitors: list[str] = Field(default_factory=list)
    price_range_min: float = 0.0
    price_range_max: float = 0.0

class BrandLandscape(BaseModel):
    premium_brands: list[str] = Field(default_factory=list)
    budget_brands: list[str] = Field(default_factory=list)
    user_brand_position: str

class BrandPosition(BaseModel):
    position: str = Field(default="")
    strength: str = Field(default="")
    weakness: str = Field(default="")
    recommendation: str = Field(default="")

    @model_validator(mode="after")
    def fill_fallbacks(self) -> "BrandPosition":
        if not self.position or not self.position.strip():
            self.position = "Orta Segment"
        if not self.strength or not self.strength.strip():
            self.strength = "Rekabetçi fiyat politikası ve ürün çeşitliliği"
        if not self.weakness or not self.weakness.strip():
            self.weakness = "Marka bilinirliği ve güven algısı geliştirilebilir"
        if not self.recommendation or not self.recommendation.strip():
            self.recommendation = "Ürün sayfasında temel değer önerisini ve fark yaratan özellikleri öne çıkarın"
        return self

class MarketGapResult(BaseModel):
    clusters: list[Cluster] = Field(..., min_length=1)
    user_product_cluster: str
    gap_opportunities: list[str] = Field(..., min_length=1)
    sentiment_based_opportunities: list[str] = Field(default_factory=list)
    trend_based_opportunities: list[str] = Field(default_factory=list)
    strategic_actions: list[str] = Field(default_factory=list)
    brand_landscape: BrandLandscape
    brand_position: BrandPosition = Field(default_factory=BrandPosition)
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
