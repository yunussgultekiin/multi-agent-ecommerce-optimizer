from pydantic import BaseModel, Field
from typing import Optional

class Variant(BaseModel):
    name: str
    price_delta: Optional[float] = None

class CompetitorResult(BaseModel):
    competitor_name: str
    price: Optional[float] = None
    features: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    review_count: Optional[int] = Field(default=None, ge=0)
    trending_keywords: list[str] = Field(default_factory=list)
    category_trends: Optional[str] = None
    source_urls: list[str] = Field(default_factory=list)
    brand: Optional[str] = None
    variants: list[Variant] = Field(default_factory=list)
    product_url: Optional[str] = None

class ToolResult(BaseModel):
    success: bool
    data: Optional[CompetitorResult] = None
    fallback_used: bool = False
    error: Optional[str] = None
