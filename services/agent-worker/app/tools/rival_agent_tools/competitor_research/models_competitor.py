from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

Platform = Literal["amazon", "trendyol", "hepsiburada"]
MIN_VALID_COMPETITORS = 3
MAX_VALID_COMPETITORS = 5

def _normalize_url_list(values: list[str]) -> list[str]:
    normalized: list[str] = []

    for value in values or []:
        if not isinstance(value, str): continue
        url = value.strip()
        if not url: continue
        if not url.startswith(("http://", "https://")): continue
        normalized.append(url)

    return list(dict.fromkeys(normalized))

def _normalize_string_list(values: list[str]) -> list[str]:
    normalized: list[str] = []

    for value in values or []:
        if not isinstance(value, str): continue
        item = value.strip()
        if item: normalized.append(item)

    return list(dict.fromkeys(normalized))

class Variant(BaseModel):
    name: str = Field(..., min_length=1)
    price_delta: Optional[float] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("variant name cannot be empty")
        return value

class CompetitorResult(BaseModel):
    competitor_name: str = Field(..., min_length=1)
    platform: Platform
    price: Optional[float] = Field(default=None, ge=0)
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

    @field_validator("competitor_name")
    @classmethod
    def normalize_competitor_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("competitor_name cannot be empty")
        return value

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("trending_keywords")
    @classmethod
    def normalize_trending_keywords(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("image_urls")
    @classmethod
    def normalize_image_urls(cls, values: list[str]) -> list[str]:
        return _normalize_url_list(values)

    @field_validator("source_urls")
    @classmethod
    def normalize_source_urls(cls, values: list[str]) -> list[str]:
        return _normalize_url_list(values)

    @field_validator("brand")
    @classmethod
    def normalize_brand(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        return value or None

    @field_validator("category_trends")
    @classmethod
    def normalize_category_trends(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        return value or None

    @field_validator("product_url")
    @classmethod
    def normalize_product_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        if not value: return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("product_url must be an http or https URL")
        
        return value

class ProductDetailsResult(BaseModel):
    competitor_name: str = Field(..., min_length=1)
    price: Optional[float] = Field(default=None, ge=0)
    features: list[str] = Field(default_factory=list)
    image_urls: list[str] = Field(default_factory=list)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    review_count: Optional[int] = Field(default=None, ge=0)
    brand: Optional[str] = None
    variants: list[Variant] = Field(default_factory=list)
    product_url: Optional[str] = None

    @field_validator("competitor_name")
    @classmethod
    def normalize_competitor_name(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError("competitor_name cannot be empty")
        return value

    @field_validator("features")
    @classmethod
    def normalize_features(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("image_urls")
    @classmethod
    def normalize_image_urls(cls, values: list[str]) -> list[str]:
        return _normalize_url_list(values)

    @field_validator("brand")
    @classmethod
    def normalize_brand(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        return value or None

    @field_validator("product_url")
    @classmethod
    def normalize_product_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        if not value: return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("product_url must be an http or https URL")

        return value

class TrendResearchResult(BaseModel):
    trending_keywords: list[str] = Field(default_factory=list)
    category_trends: Optional[str] = None

    @field_validator("trending_keywords")
    @classmethod
    def normalize_trending_keywords(cls, values: list[str]) -> list[str]:
        return _normalize_string_list(values)

    @field_validator("category_trends")
    @classmethod
    def normalize_category_trends(cls, value: Optional[str]) -> Optional[str]:
        if value is None: return None
        value = value.strip()
        return value or None


