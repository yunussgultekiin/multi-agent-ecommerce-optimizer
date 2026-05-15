from pydantic import BaseModel, Field

class VariantSeo(BaseModel):
    variant_name: str
    title_suggestion: str
    keyword_additions: list[str] = Field(default_factory=list)

class SeoOutput(BaseModel):
    title_suggestion: str = Field(..., min_length=1)
    meta_description: str = Field(..., min_length=1)
    content_recommendations: list[str] = Field(default_factory=list)
    keyword_gaps: list[str] = Field(default_factory=list)
    competitor_comparison_summary: str = Field(default="")
    platform_specific_tips: list[str] = Field(default_factory=list)
    variant_seo: list[VariantSeo] = Field(default_factory=list)
    product_development_ideas: list[str] = Field(default_factory=list)

class SeoOptimizerInput(BaseModel):
    rival_json: dict
    target_platform: str
    user_product: dict
