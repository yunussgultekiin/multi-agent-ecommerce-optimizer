from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional

Platform = Literal["amazon", "trendyol", "hepsiburada"]
MIN_VALID_COMPETITORS = 3
MAX_VALID_COMPETITORS = 10
IDEAL_RESEARCH_COUNT = 7

def _normalize_string_list(values: list[str]) -> list[str]:
    result: list[str] = []
    for v in values or []:
        if isinstance(v, str) and v.strip():
            result.append(v.strip())
    return list(dict.fromkeys(result))

class Variant(BaseModel):
    name: str = Field(..., min_length=1)
    price_delta: Optional[float] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("variant name cannot be empty")
        return value

class CompetitorResult(BaseModel):
    competitor_name: str = Field(..., min_length=1)
    platform: Platform
    estimated_price: Optional[float] = Field(default=None, ge=0)
    currency: str = Field(default="TRY")
    features: list[str] = Field(default_factory=list)
    rating: Optional[float] = Field(default=None, ge=0.0, le=10.0)

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, value: object) -> Optional[float]:
        if value is None:
            return None
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None
        if v < 0:
            return None
        if v > 5.0:
            v = v / 2.0
        return round(min(v, 5.0), 2)
    review_count: Optional[int] = Field(default=None, ge=0)
    brand: Optional[str] = None
    variants: list[Variant] = Field(default_factory=list)
    trending_keywords: list[str] = Field(default_factory=list)
    category_trends: Optional[str] = None

    @field_validator("competitor_name")
    @classmethod
    def normalize_competitor_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("competitor_name cannot be empty")
        return value

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("trending_keywords")
    @classmethod
    def normalize_trending_keywords(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("brand")
    @classmethod
    def normalize_brand(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("category_trends")
    @classmethod
    def normalize_category_trends(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def normalize_currency_and_brand(self) -> "CompetitorResult":
        self.currency = "TRY"
        if not self.brand and self.competitor_name:
            self.brand = self.competitor_name.split()[0]
        return self
