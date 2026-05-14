# services/agent-worker/app/tools/rival_agent_tools/competitor_discovery/models_discovery.py

from typing import Literal, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, Field, field_validator

Platform = Literal["amazon", "trendyol", "hepsiburada"]

PLATFORM_DOMAINS = {
    "trendyol": "trendyol.com",
    "amazon": "amazon.com.tr",
    "hepsiburada": "hepsiburada.com",
}

MIN_COMPETITORS = 3
TARGET_COMPETITORS = 5
MAX_COMPETITORS = 5


class RawDiscoveredCompetitor(BaseModel):
    competitor_name: str = Field(..., min_length=2)
    platform: Platform
    source_url_index: Optional[int] = Field(default=None, ge=0)

    # Backward-compatible only. We do NOT trust this as final product_url.
    product_url: Optional[str] = None

    @field_validator("competitor_name")
    @classmethod
    def normalize_competitor_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("competitor_name cannot be empty")
        return value

    @field_validator("product_url")
    @classmethod
    def normalize_product_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        value = value.strip()
        if not value:
            return None

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return None

        return value


class RawDiscoveryResult(BaseModel):
    competitors: list[RawDiscoveredCompetitor] = Field(
        ...,
        min_length=1,
        max_length=MAX_COMPETITORS + 5,
    )


class DiscoveredCompetitor(BaseModel):
    competitor_name: str = Field(..., min_length=2)
    product_url: str
    platform: Platform
    source_url_index: Optional[int] = None

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
    resolved_source_urls: list[str] = Field(default_factory=list)

    rejected_url_count: int = 0
    duplicate_pid_count: int = 0
    rejected_ungrounded_url_count: int = 0
    source_index_used_count: int = 0
    fallback_source_pick_count: int = 0

    @field_validator("source_urls")
    @classmethod
    def normalize_source_urls(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []

        for value in values or []:
            if not isinstance(value, str):
                continue

            url = value.strip()
            if url.startswith(("http://", "https://")):
                normalized.append(url)

        return list(dict.fromkeys(normalized))

    @field_validator("resolved_source_urls")
    @classmethod
    def normalize_resolved_source_urls(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []

        for value in values or []:
            if not isinstance(value, str):
                continue

            url = value.strip()
            if url.startswith(("http://", "https://")):
                normalized.append(url)

        return list(dict.fromkeys(normalized))