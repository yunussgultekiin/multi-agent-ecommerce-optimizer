from typing import Literal
from pydantic import BaseModel, Field, field_validator

Platform = Literal["amazon", "trendyol", "hepsiburada"]

MIN_COMPETITORS = 3
TARGET_COMPETITORS = 10

PLATFORM_SITES = {
    "trendyol": "site:trendyol.com",
    "amazon": "site:amazon.com.tr",
    "hepsiburada": "site:hepsiburada.com",
}


class DiscoveredCompetitor(BaseModel):
    competitor_name: str = Field(..., min_length=2)
    platform: Platform
    reason: str = Field(default="")

    @field_validator("competitor_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("competitor_name cannot be empty")
        return value

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else ""


class RawDiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(..., min_length=1)


class DiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(..., min_length=MIN_COMPETITORS)
