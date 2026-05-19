from pydantic import BaseModel, Field, field_validator
from typing import Literal

Platform = Literal["amazon", "trendyol", "hepsiburada"]
MIN_COMPETITORS = 3
TARGET_COMPETITORS = 10
PRIMARY_RELEVANCE_THRESHOLD = 60
SECONDARY_RELEVANCE_THRESHOLD = 45
RELEVANCE_THRESHOLD = SECONDARY_RELEVANCE_THRESHOLD

PLATFORM_SITES = {
    "trendyol": "site:trendyol.com",
    "amazon": "site:amazon.com.tr",
    "hepsiburada": "site:hepsiburada.com",
}

class DiscoveredCompetitor(BaseModel):
    competitor_name: str = Field(..., min_length=2)
    platform: Platform
    reason: str = Field(default="")
    similarity_score: int = Field(default=50, ge=0, le=100)
    similarity_label: str = Field(default="Orta")
    similarity_reason: str = Field(default="")

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

    @field_validator("similarity_label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        valid = {"Yüksek", "Orta", "Düşük"}
        return value.strip() if isinstance(value, str) and value.strip() in valid else "Orta"

    @field_validator("similarity_score", mode="before")
    @classmethod
    def normalize_score(cls, value: object) -> int:
        try:
            v = int(float(str(value)))
            return max(0, min(100, v))
        except (TypeError, ValueError):
            return 50

    @property
    def is_relevant(self) -> bool:
        return self.similarity_score >= RELEVANCE_THRESHOLD

class RawDiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(..., min_length=1)

class DiscoveryResult(BaseModel):
    competitors: list[DiscoveredCompetitor] = Field(..., min_length=MIN_COMPETITORS)
