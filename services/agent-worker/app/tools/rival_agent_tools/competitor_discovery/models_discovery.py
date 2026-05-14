from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator, model_validator

Platform = Literal["amazon", "trendyol", "hepsiburada"]

PLATFORM_DOMAINS = {
    "trendyol": "trendyol.com",
    "amazon": "amazon.com.tr",
    "hepsiburada": "hepsiburada.com",
}

MIN_COMPETITORS = 3
TARGET_COMPETITORS = 5
MAX_COMPETITORS = 5

class DiscoveredCompetitor(BaseModel):
    competitor_name: str = Field(..., min_length=2)
    product_url: str
    platform: Platform

    @field_validator("competitor_name")
    @classmethod
    def normalize_competitor_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("competitor_name cannot be empty")

        return value

    @field_validator("product_url")
    @classmethod
    def validate_product_url(cls, value: str) -> str:
        value = value.strip()
        parsed = urlparse(value)

        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("product_url must be a valid http or https URL")

        return value

    @field_validator("platform")
    @classmethod
    def validate_platform_domain(cls, value: Platform, info):
        product_url = info.data.get("product_url")

        if product_url:
            domain = PLATFORM_DOMAINS[value]
            netloc = urlparse(product_url).netloc.lower()

            if domain not in netloc:
                raise ValueError(f"product_url must be on {domain}")

        return value


class DiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(
        ...,
        min_length=MIN_COMPETITORS,
        max_length=MAX_COMPETITORS,
    )
    source_urls: list[str] = Field(default_factory=list)

    @field_validator("source_urls")
    @classmethod
    def normalize_source_urls(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []

        for value in values or []:
            if not isinstance(value, str): continue
            url = value.strip()

            if url.startswith(("http://", "https://")):
                normalized.append(url)

        return list(dict.fromkeys(normalized))

    @model_validator(mode="after")
    def remove_duplicate_competitors(self):
        unique_competitors: list[DiscoveredCompetitor] = []
        seen_urls: set[str] = set()
        seen_names: set[str] = set()

        for competitor in self.competitors:
            normalized_url = competitor.product_url.strip().lower()
            normalized_name = " ".join(
                competitor.competitor_name.strip().lower().split()
            )

            if normalized_url in seen_urls: continue
            if normalized_name in seen_names: continue
            seen_urls.add(normalized_url)
            seen_names.add(normalized_name)
            unique_competitors.append(competitor)

        if len(unique_competitors) < MIN_COMPETITORS:
            raise ValueError(
                f"At least {MIN_COMPETITORS} unique valid competitors are required"
            )
        
        self.competitors = unique_competitors[:MAX_COMPETITORS]
        return self

